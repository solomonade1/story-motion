//! StoryMotion Studio desktop shell.
//!
//! Responsibilities (and nothing more - see docs/architecture/ADR-0009 and ADR-0010):
//!  1. start the Python worker as a supervised child process (stdin piped: closing it makes the worker exit);
//!  2. read the worker's one-line JSON "ready" message (port + session token);
//!  3. open ONE window that may only show that worker's local address, with the token in the URL fragment;
//!  4. offer the native file chooser (and nothing else) to that page;
//!  5. stop the worker when the app closes, and never leave an orphan (Windows job object).
//! The shell has no commands of its own, runs no shell commands for the page, and exposes no file access.

use std::fs::{self, File};
use std::io::{BufRead, BufReader, Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

use serde::Deserialize;
use tauri::{Manager, RunEvent, Url, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_dialog::{DialogExt, MessageDialogKind};

const START_TIMEOUT: Duration = Duration::from_secs(30);
const STOP_GRACE: Duration = Duration::from_secs(5);

#[derive(Deserialize, Clone, Debug)]
struct Ready {
    event: String,
    port: u16,
    token: String,
}

struct Worker {
    child: Child,
    stdin: Option<ChildStdin>,
}

#[derive(Default)]
struct WorkerState(Mutex<Option<Worker>>);

struct WorkerConfig {
    python: PathBuf,
    repo: PathBuf,
    workspace: PathBuf,
    dist: PathBuf,
    log: PathBuf,
}

/// Development layout: the repository's own virtual environment and built UI.
/// (Bundling a private Python + FFmpeg + Piper is the packaging step, still to do; it needs a licensing decision.)
fn resolve_config(app: &tauri::AppHandle) -> Result<WorkerConfig, String> {
    let repo = std::env::var_os("STORYMOTION_REPO").map(PathBuf::from).unwrap_or_else(|| {
        Path::new(env!("CARGO_MANIFEST_DIR")).ancestors().nth(3).unwrap_or(Path::new(".")).to_path_buf()
    });
    let python = std::env::var_os("STORYMOTION_PYTHON")
        .map(PathBuf::from)
        .unwrap_or_else(|| repo.join(".venv").join("Scripts").join("python.exe"));
    let workspace = std::env::var_os("STORYMOTION_WORKSPACE").map(PathBuf::from).unwrap_or_else(|| {
        app.path().document_dir().unwrap_or_else(|_| PathBuf::from(".")).join("StoryMotion Studio")
    });
    let dist = repo.join("apps").join("desktop").join("dist");
    if !python.is_file() {
        return Err(format!(
            "The Python worker was not found at {}.\nRun the setup in the README (create the .venv and install the project), \
             or set STORYMOTION_PYTHON.",
            python.display()
        ));
    }
    if !dist.join("index.html").is_file() {
        return Err(format!("The app screens are not built ({} is missing).\nRun 'npm run build' in apps/desktop.", dist.display()));
    }
    fs::create_dir_all(&workspace).map_err(|e| format!("The workspace folder {} cannot be created: {e}", workspace.display()))?;
    let log = workspace.join("shell-worker.log");
    Ok(WorkerConfig { python, repo, workspace, dist, log })
}

fn tail(path: &Path, max: usize) -> String {
    let mut s = String::new();
    if let Ok(mut f) = File::open(path) {
        let _ = f.read_to_string(&mut s);
    }
    let start = s.len().saturating_sub(max);
    s[s.char_indices().map(|(i, _)| i).find(|i| *i >= start).unwrap_or(0)..].trim().to_string()
}

fn start_worker(cfg: &WorkerConfig) -> Result<(Worker, Ready), String> {
    let log = File::create(&cfg.log).map_err(|e| format!("Cannot write {}: {e}", cfg.log.display()))?;
    let mut cmd = Command::new(&cfg.python);
    cmd.current_dir(&cfg.repo)
        .args(["-m", "storymotion_media", "serve", "--workspace"])
        .arg(&cfg.workspace)
        .args(["--exit-on-stdin-close", "--static"])
        .arg(&cfg.dist)
        .env("PYTHONUTF8", "1")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::from(log));
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
    }
    let mut child = cmd.spawn().map_err(|e| format!("The worker could not be started: {e}"))?;
    let stdout = child.stdout.take().ok_or("The worker has no output channel.")?;
    let stdin = child.stdin.take();

    let (tx, rx) = mpsc::channel::<String>();
    thread::spawn(move || {
        let mut reader = BufReader::new(stdout);
        let mut line = String::new();
        let _ = reader.read_line(&mut line);
        let _ = tx.send(line);
        let mut sink = String::new(); // keep draining so the worker can never block on a full pipe
        while reader.read_line(&mut sink).map(|n| n > 0).unwrap_or(false) {
            sink.clear();
        }
    });

    let fail = |child: &mut Child, why: String| -> String {
        let _ = child.kill();
        let _ = child.wait();
        let log_tail = tail(&cfg.log, 600);
        if log_tail.is_empty() { why } else { format!("{why}\n\nWorker log:\n{log_tail}") }
    };
    match rx.recv_timeout(START_TIMEOUT) {
        Ok(line) => match serde_json::from_str::<Ready>(line.trim()) {
            Ok(ready) if ready.event == "ready" => Ok((Worker { child, stdin }, ready)),
            _ => Err(fail(&mut child, "The worker stopped before it was ready.".to_string())),
        },
        Err(_) => Err(fail(&mut child, "The worker did not start within 30 seconds.".to_string())),
    }
}

fn stop_worker(w: &mut Worker) {
    drop(w.stdin.take()); // the worker notices the closed pipe and exits cleanly
    let end = Instant::now() + STOP_GRACE;
    loop {
        match w.child.try_wait() {
            Ok(Some(_)) => return,
            Ok(None) if Instant::now() < end => thread::sleep(Duration::from_millis(50)),
            _ => break,
        }
    }
    let _ = w.child.kill();
    let _ = w.child.wait();
}

/// Smoke-test helper: one authenticated health request using nothing but the standard library.
fn health_check(port: u16, token: &str) -> Result<String, String> {
    let addr = ("127.0.0.1", port).to_socket_addrs().map_err(|e| e.to_string())?.next().ok_or("no address")?;
    let mut s = TcpStream::connect_timeout(&addr, Duration::from_secs(5)).map_err(|e| e.to_string())?;
    s.set_read_timeout(Some(Duration::from_secs(10))).ok();
    let req = format!("GET /api/health HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nAuthorization: Bearer {token}\r\nConnection: close\r\n\r\n");
    s.write_all(req.as_bytes()).map_err(|e| e.to_string())?;
    let mut resp = String::new();
    s.read_to_string(&mut resp).map_err(|e| e.to_string())?;
    let status_ok = resp.starts_with("HTTP/1.1 200");
    let body = resp.split("\r\n\r\n").nth(1).unwrap_or("").to_string();
    if status_ok { Ok(body) } else { Err(format!("unexpected response: {}", resp.lines().next().unwrap_or(""))) }
}

fn show_error(app: &tauri::AppHandle, msg: &str) {
    app.dialog().message(msg.to_string()).title("StoryMotion Studio").kind(MessageDialogKind::Error).blocking_show();
}

fn boot(app: tauri::AppHandle) {
    let cfg = match resolve_config(&app) {
        Ok(c) => c,
        Err(e) => {
            show_error(&app, &e);
            app.exit(1);
            return;
        }
    };
    let (worker, ready) = match start_worker(&cfg) {
        Ok(v) => v,
        Err(e) => {
            show_error(&app, &format!("StoryMotion could not start.\n\n{e}"));
            app.exit(1);
            return;
        }
    };
    *app.state::<WorkerState>().0.lock().unwrap() = Some(worker);

    let origin_port = ready.port;
    let url = Url::parse(&format!("http://127.0.0.1:{}/#token={}", ready.port, ready.token)).expect("valid local URL");
    let loaded = Arc::new(AtomicBool::new(false));
    let loaded_flag = loaded.clone();
    let built = WebviewWindowBuilder::new(&app, "main", WebviewUrl::External(url))
        .title("StoryMotion Studio")
        .inner_size(1200.0, 800.0)
        .min_inner_size(640.0, 480.0)
        // The window may only ever show the worker's own address: no other site, no other port.
        .on_navigation(move |u: &Url| u.scheme() == "http" && u.host_str() == Some("127.0.0.1") && u.port() == Some(origin_port))
        .on_page_load(move |_w, payload| {
            if matches!(payload.event(), tauri::webview::PageLoadEvent::Finished) {
                loaded_flag.store(true, Ordering::SeqCst);
            }
        })
        .build();
    if let Err(e) = built {
        show_error(&app, &format!("The window could not be opened: {e}"));
        app.exit(1);
        return;
    }

    // Automated smoke test: STORYMOTION_SMOKE_OUT=<file> makes the app prove it works, then quit.
    if let Some(out) = std::env::var_os("STORYMOTION_SMOKE_OUT") {
        let deadline = Instant::now() + Duration::from_secs(30);
        while !loaded.load(Ordering::SeqCst) && Instant::now() < deadline {
            thread::sleep(Duration::from_millis(100));
        }
        let health = health_check(ready.port, &ready.token);
        let report = serde_json::json!({
            "pageLoaded": loaded.load(Ordering::SeqCst),
            "healthOk": health.is_ok(),
            "health": health.as_ref().ok().and_then(|b| serde_json::from_str::<serde_json::Value>(b).ok()),
            "healthError": health.err(),
            "workerPid": app.state::<WorkerState>().0.lock().unwrap().as_ref().map(|w| w.child.id()),
        });
        let _ = fs::write(out, report.to_string());
        app.exit(0);
    }
}

#[cfg(windows)]
mod win {
    use std::mem::{size_of, zeroed};
    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation, SetInformationJobObject,
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };
    use windows_sys::Win32::System::Threading::GetCurrentProcess;

    /// Put this process in a job that kills every member when the last handle closes (i.e. when we exit, even by crash).
    /// Children started afterwards inherit membership, so the worker - and the venv launcher's child - can never be orphaned.
    pub fn contain_process_tree() {
        unsafe {
            let job = CreateJobObjectW(std::ptr::null(), std::ptr::null());
            if job.is_null() {
                return;
            }
            let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = zeroed();
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            let ok = SetInformationJobObject(
                job,
                JobObjectExtendedLimitInformation,
                &info as *const _ as *const core::ffi::c_void,
                size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            );
            if ok != 0 {
                AssignProcessToJobObject(job, GetCurrentProcess());
            }
            // The handle is deliberately never closed: the OS closes it when this process ends, which triggers the kill.
        }
    }
}

pub fn run() {
    #[cfg(windows)]
    win::contain_process_tree();

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(WorkerState::default())
        .setup(|app| {
            let handle = app.handle().clone();
            thread::spawn(move || boot(handle)); // the event loop stays responsive while the worker starts
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building StoryMotion Studio");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(mut w) = handle.state::<WorkerState>().0.lock().unwrap().take() {
                stop_worker(&mut w);
            }
        }
    });
}
