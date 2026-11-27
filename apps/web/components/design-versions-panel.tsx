"use client";

import { useState, type FormEvent } from "react";

import { api, toApiError } from "../lib/api";
import { typeLabels, type DesignState } from "../lib/design";
import { formatValue, sideLabel, type Comparison, type VersionDetail, type VersionList } from "../lib/design-versions";
import { useResource } from "../lib/use-resource";

const fa = (value: number) => value.toLocaleString("fa-IR");

function Comments({ projectId, number, canComment, reloadKey, onPosted }: { projectId: string; number: string; canComment: boolean; reloadKey: number; onPosted: () => void }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const detail = useResource<VersionDetail>(`/projects/${projectId}/design/versions/${number}`, reloadKey);
  const elements = detail.data ? detail.data.data.elements : [];

  function post(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const body: Record<string, unknown> = { body: String(data.get("body") ?? "") };
    if (data.get("element")) body.element_id = String(data.get("element"));
    setBusy(true);
    setMessage(null);
    api
      .post(`/projects/${projectId}/design/versions/${number}/comments`, body)
      .then(() => {
        form.reset();
        setMessage({ kind: "ok", text: "نظر ثبت شد." });
        onPosted();
      })
      .catch((error) => setMessage({ kind: "error", text: toApiError(error).userMessage }))
      .finally(() => setBusy(false));
  }

  return (
    <>
      {detail.error ? <p className="alert alert-error" role="alert">{detail.error.userMessage}</p> : null}
      {message ? (
        <div role={message.kind === "ok" ? "status" : "alert"} className={`alert alert-${message.kind === "ok" ? "success" : "error"}`}>
          {message.text}
        </div>
      ) : null}
      {detail.data && detail.data.comments.length > 0 ? (
        <ul className="flag-list">
          {detail.data.comments.map((item) => (
            <li key={item.id}>
              {item.element_id ? `[${item.element_id}] ` : ""}{item.body} — {item.author}
            </li>
          ))}
        </ul>
      ) : (
        <p className="field-hint">برای این نسخه نظری ثبت نشده است.</p>
      )}
      {canComment ? (
        <form onSubmit={post}>
          <label>عنصر (اختیاری)
            <select name="element" defaultValue="">
              <option value="">کل نسخه</option>
              {elements.map((e) => <option key={e.id} value={e.id}>{e.id} — {typeLabels[e.type]}</option>)}
            </select>
          </label>
          <label>متن نظر<textarea name="body" maxLength={2000} required /></label>
          <button className="button" type="submit" disabled={busy}>ثبت نظر</button>
        </form>
      ) : null}
    </>
  );
}

export function DesignVersionsPanel({ projectId, canSave, canComment, version }: { projectId: string; canSave: boolean; canComment: boolean; version: number }) {
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [first, setFirst] = useState("");
  const [second, setSecond] = useState("current");
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [viewed, setViewed] = useState("");
  const key = version + reload;
  const design = useResource<DesignState>(`/projects/${projectId}/design`, key);
  const list = useResource<VersionList>(`/projects/${projectId}/design/versions`, key);
  const versions = list.data?.versions ?? [];
  const firstChoice = first || (versions[1] ?? versions[0])?.number.toString() || "";
  const viewedChoice = viewed || versions[0]?.number.toString() || "";
  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    setMessage(null);
    try {
      await action();
      setMessage({ kind: "ok", text: success });
    } catch (error) {
      setMessage({ kind: "error", text: toApiError(error).userMessage });
    } finally {
      setBusy(false);
      setReload((value) => value + 1);
    }
  }

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const label = String(new FormData(form).get("label") ?? "");
    if (!design.data) return;
    void run(async () => {
      await api.post(`/projects/${projectId}/design/versions`, { version: design.data?.version, label });
      form.reset();
    }, "نسخه ذخیره شد.");
  }

  function compare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    api
      .get<Comparison>(`/projects/${projectId}/design/compare?a=${encodeURIComponent(firstChoice)}&b=${encodeURIComponent(second)}`)
      .then(setComparison)
      .catch((error) => {
        setComparison(null);
        setMessage({ kind: "error", text: toApiError(error).userMessage });
      })
      .finally(() => setBusy(false));
  }

  const options = (
    <>
      {versions.map((item) => (
        <option key={item.number} value={item.number}>نسخهٔ {fa(item.number)} — {item.label}</option>
      ))}
    </>
  );

  return (
    <section className="detail-section" aria-labelledby="versions-title">
      <h2 id="versions-title">نسخه‌ها، مقایسه و نظرات طرح</h2>
      <p className="field-hint">
        نسخهٔ ذخیره‌شده عکس ثابتی از طرح است و بعداً تغییر نمی‌کند. مقایسه عناصر را با شناسهٔ ثابتشان تطبیق می‌دهد.
      </p>
      {list.error ? <p className="alert alert-error" role="alert">{list.error.userMessage}</p> : null}
      {message ? (
        <div role={message.kind === "ok" ? "status" : "alert"} className={`alert alert-${message.kind === "ok" ? "success" : "error"}`}>
          {message.text}
        </div>
      ) : null}

      {canSave ? (
        <form onSubmit={save}>
          <label>عنوان نسخه<input name="label" maxLength={120} required /></label>
          <button className="button" type="submit" disabled={busy || !design.data?.exists}>ذخیرهٔ نسخهٔ جدید</button>
        </form>
      ) : null}

      {versions.length === 0 ? (
        <p className="field-hint">هنوز نسخه‌ای ذخیره نشده است.</p>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <caption className="visually-hidden">نسخه‌های ذخیره‌شده</caption>
              <thead>
                <tr><th scope="col">نسخه</th><th scope="col">عنوان</th><th scope="col">سازنده</th><th scope="col">عناصر</th><th scope="col">نظرات</th></tr>
              </thead>
              <tbody>
                {versions.map((item) => (
                  <tr key={item.number}>
                    <td>{fa(item.number)}</td><td>{item.label}</td><td>{item.author}</td><td>{fa(item.element_count)}</td><td>{fa(item.comment_count)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <form onSubmit={compare}>
            <label>مقایسهٔ<select value={firstChoice} onChange={(event) => setFirst(event.target.value)}>{options}</select></label>
            <label>با<select value={second} onChange={(event) => setSecond(event.target.value)}><option value="current">طرح فعلی</option>{options}</select></label>
            <button className="button" type="submit" disabled={busy || !firstChoice}>مقایسه</button>
          </form>

          {comparison ? (
            <div aria-live="polite">
              <h3>{sideLabel(comparison.from)} ← {sideLabel(comparison.to)}</h3>
              <p role="status">
                {fa(comparison.summary.added)} عنصر اضافه، {fa(comparison.summary.removed)} حذف و {fa(comparison.summary.changed)} تغییرکرده؛ {fa(comparison.unchanged)} بدون تغییر.
              </p>
              <div className="table-wrap">
                <table>
                  <caption className="visually-hidden">عناصر تغییرکرده بین دو نسخه</caption>
                  <thead>
                    <tr><th scope="col">عنصر</th><th scope="col">وضعیت</th><th scope="col">جزئیات</th></tr>
                  </thead>
                  <tbody>
                    {comparison.added.map((e) => <tr key={`a${e.id}`}><td>{e.id} — {typeLabels[e.type]}</td><td>اضافه شد</td><td>طبقهٔ {fa(e.floor)}</td></tr>)}
                    {comparison.removed.map((e) => <tr key={`r${e.id}`}><td>{e.id} — {typeLabels[e.type]}</td><td>حذف شد</td><td>طبقهٔ {fa(e.floor)}</td></tr>)}
                    {comparison.changed.map((e) => (
                      <tr key={`c${e.id}`}>
                        <td>{e.id} — {typeLabels[e.type]}</td>
                        <td>تغییر کرد</td>
                        <td>{e.fields.map((f) => `${f.field}: ${formatValue(f.before)} ← ${formatValue(f.after)}`).join("؛ ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          <h3>نظرات</h3>
          <label>نسخه<select value={viewedChoice} onChange={(event) => setViewed(event.target.value)}>{options}</select></label>
          <Comments projectId={projectId} number={viewedChoice} canComment={canComment} reloadKey={key} onPosted={() => setReload((value) => value + 1)} />
        </>
      )}
    </section>
  );
}
