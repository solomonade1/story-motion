import { useMemo, useState } from "react";
import { ApiClient, readConfig, workerPickerEnabled, type Api } from "./api";
import { enableWorkerPicker } from "./native";
import { ProjectScreen } from "./Project";
import { Projects } from "./Projects";
import { Setup } from "./Setup";

type Route = { name: "setup" } | { name: "projects" } | { name: "project"; id: string };

/** `api` is injectable so tests (and a future shell) can supply their own client. */
export function App(props: { api?: Api }) {
  const api = useMemo<Api | null>(() => {
    if (props.api) return props.api;
    const cfg = readConfig(window.location);
    if (!cfg) return null;
    const client = new ApiClient(cfg);
    enableWorkerPicker(workerPickerEnabled(window.location) ? (o) => client.pick({ kind: o.directory ? "folder" : "files", multiple: o.multiple ?? false, ...(o.extensions ? { extensions: o.extensions } : {}), ...(o.filterName ? { filterName: o.filterName } : {}) }) : null);
    return client;
  }, [props.api]);
  const [route, setRoute] = useState<Route>({ name: "setup" });

  if (!api) {
    return (
      <main className="page narrow">
        <h1>StoryMotion Studio</h1>
        <p role="alert">
          This page needs to be opened from the StoryMotion app, which gives it a private session key. Close this tab and start StoryMotion
          again.
        </p>
      </main>
    );
  }
  if (route.name === "setup") return <Setup api={api} onContinue={() => setRoute({ name: "projects" })} />;
  if (route.name === "projects") {
    return <Projects api={api} onOpen={(id) => setRoute({ name: "project", id })} onSetup={() => setRoute({ name: "setup" })} />;
  }
  return <ProjectScreen api={api} projectId={route.id} onBack={() => setRoute({ name: "projects" })} />;
}
