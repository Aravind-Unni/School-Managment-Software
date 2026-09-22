/**
 * Read-only view of the installed school configuration from the registry API.
 */

import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "@shared/i18n/LanguageContext";
import { getSchoolConfig, type SchoolConfig } from "./api";
import { loadErrorKey } from "./loadErrorKey";
import { Loading } from "@shared/ui/Loading";

type LoadState =
  | { readonly status: "loading" }
  | { readonly status: "ready"; readonly config: SchoolConfig }
  | { readonly status: "error"; readonly messageKey: string };

/** School setup screen: shows config returned by GET /api/v1/school-config. */
export function SchoolSetupPage() {
  const { t } = useLanguage();
  const [state, setState] = useState<LoadState>({ status: "loading" });

  const load = useCallback(async () => {
    setState({ status: "loading" });
    try {
      const config = await getSchoolConfig();
      setState({ status: "ready", config });
    } catch (error) {
      setState({ status: "error", messageKey: loadErrorKey(error) });
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return (
    <section>
      <h1>{t("registry.setup_title")}</h1>
      {state.status === "loading" && <Loading />}
      {state.status === "error" && (
        <p role="alert">
          {t(state.messageKey)}{" "}
          <button type="button" onClick={() => void load()}>
            {t("ui.retry")}
          </button>
        </p>
      )}
      {state.status === "ready" && (
        <dl>
          <div>
            <dt>{t("registry.setup_title")}</dt>
            <dd>{state.config.display_name}</dd>
          </div>
          <div>
            <dt>{t("registry.board")}</dt>
            <dd>{state.config.board}</dd>
          </div>
          <div>
            <dt>{t("registry.default_language")}</dt>
            <dd>{state.config.default_language}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
