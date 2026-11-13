import { useEffect, useMemo, useState } from "react";
import "./App.css";

const API_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/$/, "");

const EMPTY_FORM = {
  prospectName: "",
  prospectEmail: "",
  designation: "",
  company: "",
  website: "",
  senderCompany: "",
  product: "",
  valueProposition: "",
};

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: "grid" },
  { id: "new", label: "New Outreach", icon: "plus" },
  { id: "history", label: "History", icon: "clock" },
  { id: "inbox", label: "Inbox", icon: "mail" },
];

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : {};
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map((item) => item.msg).join("; ") : data.detail;
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return data;
}

function App() {
  const [page, setPage] = useState(() => window.location.hash.replace("#", "") || "dashboard");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [selectedCampaign, setSelectedCampaign] = useState(null);
  const [humanApproved, setHumanApproved] = useState(false);
  const [emailDraft, setEmailDraft] = useState({ subject: "", body: "" });
  const [gmail, setGmail] = useState({ connected: false, email: null });
  const [gmailLoading, setGmailLoading] = useState(false);
  const [gmailNotice, setGmailNotice] = useState("");
  const [inbox, setInbox] = useState([]);

  const navigate = (nextPage) => {
    if (nextPage === "new") {
      setForm(EMPTY_FORM);
      setResult(null);
      setEmailDraft({ subject: "", body: "" });
      setHumanApproved(false);
      setError("");
      window.sessionStorage.removeItem("prospectiq.oauth.workspace");
    }
    setPage(nextPage);
    window.history.pushState({}, "", `#${nextPage}`);
    setMobileNavOpen(false);
    if (nextPage !== "history") setSelectedCampaign(null);
  };

  const loadHistory = async () => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const data = await request("/api/history");
      setHistory(data.items || []);
    } catch (err) {
      setHistoryError(err instanceof TypeError ? "History is unavailable. Make sure the FastAPI backend is running." : err.message);
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadGmail = async () => {
    try { setGmail(await request("/api/gmail/status")); } catch { setGmail({ connected: false, email: null }); }
  };

  const loadInbox = async () => {
    try { const data = await request("/api/inbox"); setInbox(data.items || []); } catch { setInbox([]); }
  };

  const restoreOAuthWorkspace = () => {
    const saved = window.sessionStorage.getItem("prospectiq.oauth.workspace");
    if (!saved) return;
    try {
      const workspace = JSON.parse(saved);
      if (workspace.form) setForm({ ...EMPTY_FORM, ...workspace.form });
      if (workspace.result) setResult(workspace.result);
      if (workspace.emailDraft) setEmailDraft(workspace.emailDraft);
      setHumanApproved(Boolean(workspace.humanApproved));
      if (["dashboard", "new", "history", "inbox"].includes(workspace.page)) {
        setPage(workspace.page);
        window.history.replaceState({}, "", `#${workspace.page}`);
      }
      window.sessionStorage.removeItem("prospectiq.oauth.workspace");
    } catch {
      setGmailNotice("Your Gmail connection returned, but the saved outreach session could not be restored.");
    }
  };

  useEffect(() => {
    const handleHashChange = () => {
      const nextPage = window.location.hash.replace("#", "") || "dashboard";
      setPage(["dashboard", "new", "history", "inbox"].includes(nextPage) ? nextPage : "dashboard");
    };
    window.addEventListener("hashchange", handleHashChange);
    const initialLoad = window.setTimeout(() => {
      restoreOAuthWorkspace();
      const oauthResult = new URLSearchParams(window.location.search).get("gmail");
      if (oauthResult === "connected") setGmailNotice("Gmail Connected");
      if (oauthResult === "denied") setGmailNotice("Gmail connection was cancelled. Your outreach work is still here.");
      if (oauthResult === "error") setGmailNotice("Gmail connection failed. Your outreach work is still here.");
      if (oauthResult) window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash}`);
      loadHistory();
      loadGmail();
      loadInbox();
    }, 0);
    return () => {
      window.clearTimeout(initialLoad);
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, []);

  const handleChange = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    setHumanApproved(false);
    try {
      const data = await request("/api/outreach/generate", {
        method: "POST",
        body: JSON.stringify({
          prospect_name: form.prospectName.trim(),
          prospect_email: form.prospectEmail.trim(),
          designation: form.designation.trim(),
          company: form.company.trim(),
          company_website: form.website.trim() || null,
          sender_company: form.senderCompany.trim(),
          product_or_service: form.product.trim(),
          value_proposition: form.valueProposition.trim(),
        }),
      });
      if (!data.success || !data.research || !data.signals || !data.email || !data.review) throw new Error("The backend returned an incomplete outreach response.");
      setResult(data);
      setEmailDraft({ subject: data.email?.subject || "", body: data.email?.email_body || "" });
      await loadHistory();
    } catch (err) {
      setError(err instanceof TypeError ? "Unable to connect to FastAPI. Start the backend at http://127.0.0.1:8000." : err.message || "Something went wrong while generating outreach.");
    } finally {
      setLoading(false);
    }
  };

  const approveDraft = async () => {
    if (!result?.history_id || sending) return;
    setSending(true);
    setError("");
    try {
      await request(`/api/history/${result.history_id}/approval`, { method: "PATCH", body: JSON.stringify({ approved: true }) });
      const idempotencyKey = `campaign-${result.history_id}-${crypto.randomUUID()}`;
      await request(`/api/history/${result.history_id}/send`, { method: "POST", body: JSON.stringify({ subject: emailDraft.subject.trim(), body: emailDraft.body.trim(), idempotency_key: idempotencyKey }) });
      setHumanApproved(true);
      await loadHistory();
      await loadInbox();
    } catch (err) {
      setError(err.message || "The email could not be sent.");
    } finally {
      setSending(false);
    }
  };

  const connectGmail = (forceReconnect = false) => {
    if (gmail.connected && !forceReconnect) {
      setGmailNotice("Gmail is already connected.");
      return;
    }
    try {
      window.sessionStorage.setItem("prospectiq.oauth.workspace", JSON.stringify({
        page: activePage,
        form,
        result,
        emailDraft,
        humanApproved,
        savedAt: new Date().toISOString(),
      }));
      setGmailLoading(true);
      window.location.replace(`${API_URL}/api/gmail/connect?return_to=${encodeURIComponent(window.location.origin)}`);
    } catch {
      setGmailNotice("Unable to save this outreach session before connecting Gmail.");
    }
  };
  const disconnectGmail = async () => {
    setGmailLoading(true);
    try {
      await request("/api/gmail/connection", { method: "DELETE" });
      setGmail({ connected: false, email: null });
      setGmailNotice("Gmail disconnected.");
    } catch (err) {
      setGmailNotice(err.message || "Gmail could not be disconnected.");
    } finally {
      setGmailLoading(false);
    }
  };

  const openCampaign = async (campaignId) => {
    if (campaignId === null) { setSelectedCampaign(null); return; }
    setHistoryError("");
    try { setSelectedCampaign(await request(`/api/history/${campaignId}`)); }
    catch (err) { setHistoryError(err.message || "Unable to open this campaign."); }
  };

  const deleteCampaign = async (campaignId) => {
    if (!window.confirm("Delete this campaign permanently?")) return;
    try {
      await request(`/api/history/${campaignId}`, { method: "DELETE" });
      if (selectedCampaign?.id === campaignId) setSelectedCampaign(null);
      await loadHistory();
    } catch (err) { setHistoryError(err.message || "Unable to delete this campaign."); }
  };

  const metrics = useMemo(() => ({
    campaigns: history.length,
    approved: history.filter((item) => item.approval_status === "approved").length,
    pending: history.filter((item) => item.approval_status === "pending").length,
    sources: history.reduce((total, item) => total + (item.source_count || 0), 0),
  }), [history]);
  const activePage = ["new", "history", "inbox"].includes(page) ? page : "dashboard";

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNavOpen ? "sidebar-open" : ""}`}>
        <div className="brand"><span className="brand-mark"><Icon name="spark" /></span><span>Prospect<span className="brand-accent">IQ</span></span></div>
        <div className="workspace-label">Workspace</div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => <button type="button" className={`nav-item ${activePage === item.id ? "active" : ""}`} key={item.id} onClick={() => navigate(item.id)}><Icon name={item.icon} /><span>{item.label}</span></button>)}
        </nav>
        <div className="sidebar-footer"><div className="sidebar-status"><span className="status-dot" /> API connected</div>{gmail.connected ? <div className="gmail-connected"><div className="gmail-account"><Icon name="mail" /><span className="gmail-email"><strong>Gmail Connected</strong><small>{gmail.email}</small></span></div><div className="gmail-actions"><button type="button" onClick={() => connectGmail(true)} disabled={gmailLoading}>Reconnect</button><button type="button" onClick={disconnectGmail} disabled={gmailLoading}>Disconnect</button></div></div> : <button type="button" className="gmail-account gmail-connect" onClick={() => connectGmail(false)} disabled={gmailLoading}><Icon name="mail" /> {gmailLoading ? "Connecting..." : "Connect Gmail"}</button>}{gmailNotice && <p className="gmail-notice">{gmailNotice}</p>}<p>Evidence-backed outreach for thoughtful sales teams.</p></div>
      </aside>
      <div className="content-shell">
        <header className="mobile-header"><button type="button" className="icon-button" onClick={() => setMobileNavOpen((open) => !open)} aria-label="Toggle navigation"><Icon name="menu" /></button><div className="brand brand-small"><span className="brand-mark"><Icon name="spark" /></span>Prospect<span className="brand-accent">IQ</span></div><button type="button" className="icon-button" onClick={() => navigate("new")} aria-label="New outreach"><Icon name="plus" /></button></header>
        {mobileNavOpen && <button className="nav-backdrop" type="button" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}
        <main className="main-content">
          {activePage === "dashboard" && <Dashboard metrics={metrics} history={history} loading={historyLoading} onNavigate={navigate} onOpen={openCampaign} />}
        {activePage === "new" && <NewOutreach form={form} loading={loading} sending={sending} error={error} result={result} emailDraft={emailDraft} gmail={gmail} gmailLoading={gmailLoading} humanApproved={humanApproved} onChange={handleChange} onEmailChange={setEmailDraft} onSubmit={handleSubmit} onApprove={approveDraft} onConnectGmail={() => connectGmail(false)} onReconnectGmail={() => connectGmail(true)} onNavigate={navigate} />}
          {activePage === "history" && <HistoryPage history={history} loading={historyLoading} error={historyError} selectedCampaign={selectedCampaign} onOpen={openCampaign} onDelete={deleteCampaign} onNavigate={navigate} />}
          {activePage === "inbox" && <InboxPage inbox={inbox} onOpen={openCampaign} onNavigate={navigate} />}
        </main>
      </div>
    </div>
  );
}

function Dashboard({ metrics, history, loading, onNavigate, onOpen }) {
  return <><PageHeader eyebrow="Workspace overview" title="Good morning, ready to find your next conversation?" description="Track evidence-backed outreach campaigns and review your latest work." action={<button type="button" className="primary-button" onClick={() => onNavigate("new")}><Icon name="plus" /> New outreach</button>} /><section className="metric-grid" aria-label="Workspace metrics"><MetricCard label="Campaigns generated" value={metrics.campaigns} icon="send" tone="blue" /><MetricCard label="Awaiting approval" value={metrics.pending} icon="clock" tone="amber" /><MetricCard label="Approved drafts" value={metrics.approved} icon="check" tone="green" /><MetricCard label="Research sources" value={metrics.sources || "—"} icon="link" tone="purple" /></section><section className="dashboard-grid"><div className="panel activity-panel"><div className="panel-heading"><div><p className="eyebrow-dark">Recent activity</p><h2>Latest campaigns</h2></div><button type="button" className="text-button" onClick={() => onNavigate("history")}>View history <Icon name="arrow" /></button></div>{loading ? <LoadingState label="Loading campaign activity..." /> : history.length === 0 ? <EmptyState icon="send" title="No campaigns yet" description="Create your first evidence-backed outreach draft to see activity here." action={<button type="button" className="secondary-button" onClick={() => onNavigate("new")}>Start an outreach</button>} /> : <div className="activity-list">{history.slice(0, 5).map((campaign) => <CampaignRow key={campaign.id} campaign={campaign} onOpen={onOpen} />)}</div>}</div><div className="panel getting-started"><p className="eyebrow-dark">A simple workflow</p><h2>From research to reply</h2><div className="workflow-steps"><WorkflowStep number="01" title="Research" text="Find current public signals." /><WorkflowStep number="02" title="Personalize" text="Connect the signal to your offer." /><WorkflowStep number="03" title="Review" text="Approve the draft before sending." /></div><button type="button" className="secondary-button full-button" onClick={() => onNavigate("new")}>Create a campaign <Icon name="arrow" /></button></div></section></>;
}

function NewOutreach({ form, loading, sending, error, result, emailDraft, gmail, gmailLoading, humanApproved, onChange, onEmailChange, onSubmit, onApprove, onConnectGmail, onReconnectGmail, onNavigate }) {
  return <><PageHeader eyebrow="New campaign" title="Create personalized outreach" description="Give ProspectIQ enough context to find a credible signal and draft a relevant first touch." />{!result ? <section className="form-panel panel"><div className="form-intro"><span className="step-badge">01 / 01</span><div><h2>Campaign details</h2><p>All required fields stay focused on the prospect and your actual offering.</p></div></div><form onSubmit={onSubmit}><FormSection title="Prospect information" description="Who are you reaching out to?" icon="user"><Input label="Prospect name" name="prospectName" placeholder="e.g. Satya Nadella" value={form.prospectName} onChange={onChange} /><Input label="Prospect email" name="prospectEmail" type="email" placeholder="prospect@company.com" value={form.prospectEmail} onChange={onChange} /><Input label="Designation" name="designation" placeholder="e.g. Chief Executive Officer" value={form.designation} onChange={onChange} /><Input label="Company" name="company" placeholder="e.g. Microsoft" value={form.company} onChange={onChange} /><Input label="Company website" name="website" placeholder="https://example.com" value={form.website} onChange={onChange} required={false} /></FormSection><FormSection title="Your offering" description="Describe the product capabilities ProspectIQ may reference." icon="briefcase"><Input label="Sender company" name="senderCompany" placeholder="e.g. DataPilot" value={form.senderCompany} onChange={onChange} /><Input label="Product or service" name="product" placeholder="e.g. AI-powered analytics platform" value={form.product} onChange={onChange} /><label className="field full-field"><span>Value proposition<em>*</em></span><textarea name="valueProposition" value={form.valueProposition} onChange={onChange} placeholder="DataPilot helps enterprises analyze business data, identify meaningful insights, and understand operational trends." required rows="5" /></label></FormSection><div className="form-actions"><p><Icon name="shield" /> Your product description is the only source used for product claims.</p><button type="submit" className="primary-button generate-button" disabled={loading}>{loading ? <><span className="spinner" /> Researching and reviewing...</> : <>Generate outreach <Icon name="arrow" /></>}</button></div></form>{loading && <div className="loading-box"><span className="spinner spinner-dark" /> ProspectIQ is researching sources, analyzing signals, writing the email, and reviewing quality.</div>}{error && <div className="error-box"><Icon name="alert" /><div><strong>Could not generate this campaign</strong><p>{error}</p></div></div>}</section> : <Results result={result} error={error} emailDraft={emailDraft} onEmailChange={onEmailChange} gmail={gmail} gmailLoading={gmailLoading} sending={sending} humanApproved={humanApproved} onApprove={onApprove} onConnectGmail={onConnectGmail} onReconnectGmail={onReconnectGmail} onNew={() => onNavigate("new")} />}</>;
}

function HistoryPage({ history, loading, error, selectedCampaign, onOpen, onDelete, onNavigate }) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const filtered = history.filter((item) => `${item.prospect_name} ${item.company}`.toLowerCase().includes(search.toLowerCase()) && (status === "all" || (item.status || item.approval_status) === status));
  return <><PageHeader eyebrow="Campaign library" title="History" description="Open, review, and manage every campaign saved by ProspectIQ." action={<button type="button" className="primary-button" onClick={() => onNavigate("new")}><Icon name="plus" /> New outreach</button>} /><section className="panel history-panel"><div className="history-toolbar"><div className="search-field"><Icon name="search" /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search prospect or company" /></div><select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Filter campaigns"><option value="all">All statuses</option><option value="sent">Sent</option><option value="replied">Replied</option><option value="failed">Failed</option><option value="awaiting_approval">Awaiting approval</option><option value="ai_review_failed">Review failed</option></select></div>{error && <div className="error-box compact"><Icon name="alert" /><p>{error}</p></div>}{loading ? <LoadingState label="Loading saved campaigns..." /> : filtered.length === 0 ? <EmptyState icon="clock" title={history.length ? "No matching campaigns" : "Your history is empty"} description={history.length ? "Try another search or status filter." : "Generated campaigns will be saved here automatically."} action={!history.length && <button type="button" className="secondary-button" onClick={() => onNavigate("new")}>Create your first campaign</button>} /> : <div className="history-table-wrap"><table className="history-table"><thead><tr><th>Prospect</th><th>Company</th><th>Generated</th><th>Review</th><th>Status</th><th><span className="sr-only">Actions</span></th></tr></thead><tbody>{filtered.map((campaign) => <tr key={campaign.id}><td><button type="button" className="table-link" onClick={() => onOpen(campaign.id)}>{campaign.prospect_name}</button><span className="table-subject">{campaign.email_subject || "Untitled draft"}</span></td><td>{campaign.company}</td><td>{formatDate(campaign.generated_at)}</td><td><span className="score-pill">{campaign.review_score ?? "—"}/100</span></td><td><StatusBadge status={campaign.status || campaign.approval_status} /></td><td><button type="button" className="row-action" onClick={() => onDelete(campaign.id)} aria-label={`Delete campaign for ${campaign.prospect_name}`}><Icon name="trash" /></button></td></tr>)}</tbody></table></div>}</section>{selectedCampaign && <CampaignDetail campaign={selectedCampaign} onClose={() => onOpen(null)} />}</>;
}

function InboxPage({ inbox, onOpen, onNavigate }) {
  return <><PageHeader eyebrow="Conversations" title="Inbox" description="Replies detected in Gmail and matched to your ProspectIQ campaigns." action={<button type="button" className="secondary-button" onClick={() => onNavigate("history")}><Icon name="clock" /> View campaigns</button>} /><section className="panel history-panel">{inbox.length === 0 ? <EmptyState icon="mail" title="No replies yet" description="When a prospect replies to a sent campaign, the conversation will appear here." action={<button type="button" className="secondary-button" onClick={() => onNavigate("new")}>Create outreach</button>} /> : <div className="history-table-wrap"><table className="history-table"><thead><tr><th>Conversation</th><th>Prospect</th><th>Last message</th><th>Reply status</th></tr></thead><tbody>{inbox.map((thread) => <tr key={thread.id}><td><button type="button" className="table-link" onClick={() => onOpen(thread.id)}>{thread.email_subject || "Untitled conversation"}</button><span className="table-subject">{thread.last_preview || "No preview"}</span></td><td>{thread.prospect_name}<span className="table-subject">{thread.prospect_email}</span></td><td>{formatDate(thread.last_message_at)}</td><td><StatusBadge status="replied" /></td></tr>)}</tbody></table></div>}</section></>;
}

function CampaignDetail({ campaign, onClose }) { return <div className="modal-layer" role="dialog" aria-modal="true"><div className="detail-modal"><div className="modal-heading"><div><p className="eyebrow-dark">Saved campaign</p><h2>{campaign.research?.prospect?.name} at {campaign.research?.prospect?.company}</h2></div><button type="button" className="icon-button" onClick={onClose} aria-label="Close campaign"><Icon name="close" /></button></div><Results result={campaign} emailDraft={{ subject: campaign.email?.subject || "", body: campaign.email?.email_body || "" }} onEmailChange={() => {}} gmail={{ connected: campaign.sending_status === "sent", email: "your Gmail account" }} humanApproved={campaign.sending_status === "sent"} onApprove={() => {}} onConnectGmail={() => {}} compact /></div></div>; }

function Results({ result, error, emailDraft, onEmailChange, gmail, gmailLoading, sending = false, humanApproved, onApprove, onConnectGmail, onReconnectGmail, onNew, compact = false }) {
  const signals = result.signals?.signals || [];
  const sources = result.research?.sources || [];
  const review = result.review || {};
  const canSend = Boolean(review.approved && emailDraft?.body?.trim() && result.history_id && gmail?.connected && !humanApproved);
  const copyEmail = async () => { if (emailDraft?.body) await navigator.clipboard?.writeText(emailDraft.body); };
  return <section className={`results-section ${compact ? "results-compact" : ""}`}>
    <div className="results-heading"><div><p className="eyebrow-dark">Campaign review</p><h2>{emailDraft?.subject || "Outreach draft"}</h2></div>{!compact && <button type="button" className="secondary-button" onClick={onNew}><Icon name="plus" /> New campaign</button>}</div>
    {error && <div className="error-box"><Icon name="alert" /><div><strong>Could not send this email</strong><p>{error}</p></div></div>}
    <div className="results-grid">
      <ResultCard number="01" title="Research summary" icon="search"><div className="summary-stats"><div><strong>{result.research?.total_sources || 0}</strong><span>Sources found</span></div><div><strong>{signals.length}</strong><span>Signals selected</span></div></div><p className="muted">Research for <strong>{result.research?.prospect?.name}</strong>, {result.research?.prospect?.company}.</p><div className="source-list">{sources.slice(0, 6).map((source, index) => <a key={source.url || index} href={source.url} target="_blank" rel="noreferrer"><Icon name="link" /><span>{source.title || source.url}</span><Icon name="external" /></a>)}</div></ResultCard>
      <ResultCard number="02" title="Business signals" icon="pulse"><p className="muted">{result.signals?.overall_assessment || "Signals identified from the available research."}</p>{signals.length ? <div className="signal-list">{signals.map((signal, index) => <div className="signal-card" key={signal.source_url || index}><div className="signal-title"><h3>{signal.title}</h3><span className="confidence">{signal.confidence || "Evidence"}</span></div><p>{signal.summary}</p><dl><div><dt>Why it matters</dt><dd>{signal.relevance_reason}</dd></div><div><dt>Opportunity</dt><dd>{signal.business_opportunity}</dd></div></dl>{signal.source_url && <a href={signal.source_url} target="_blank" rel="noreferrer" className="inline-link">View source <Icon name="external" /></a>}</div>)}</div> : <EmptyState icon="pulse" title="No relevant signals" description="The evidence was not strong enough to support a safe personalized pitch." />}</ResultCard>
      <ResultCard number="03" title="Generated email" icon="mail"><label className="field email-editor"><span>Subject</span><input value={emailDraft?.subject || ""} onChange={(event) => onEmailChange({ ...emailDraft, subject: event.target.value })} /></label><label className="field email-editor"><span>Email body</span><textarea value={emailDraft?.body || ""} onChange={(event) => onEmailChange({ ...emailDraft, body: event.target.value })} rows="9" /></label><div className="email-footer"><span><Icon name="link" /> {result.email?.personalization_signal || "No personalization signal"}</span><button type="button" className="secondary-button small-button" onClick={copyEmail}><Icon name="copy" /> Copy email</button></div></ResultCard>
      <ResultCard number="04" title="AI quality review" icon="check"><div className="review-overview"><div className={`review-score ${review.approved ? "pass" : "fail"}`}><strong>{review.quality_score ?? 0}</strong><span>/ 100</span></div><div><StatusBadge status={review.approved ? "approved" : "rejected"} /><p>{review.review_summary}</p></div></div><div className="check-grid"><ReviewCheck label="Factual accuracy" value={review.factual_accuracy} /><ReviewCheck label="Product accuracy" value={review.product_accuracy} /><ReviewCheck label="Personalization" value={review.personalization} /><ReviewCheck label="Professionalism" value={review.professionalism} /></div>{review.issues?.length > 0 && <ReviewList title="Issues to address" items={review.issues} tone="danger" />}{review.suggestions?.length > 0 && <ReviewList title="Suggestions" items={review.suggestions} />}</ResultCard>
      <ResultCard number="05" title="Approve and send" icon="send"><div className={`approval-card ${humanApproved ? "approved" : ""}`}>{humanApproved ? <><Icon name="check" /><div><strong>Email sent successfully</strong><p>The final edited email was sent through {gmail.email}. No further action is needed.</p></div></> : !gmail?.connected ? <><Icon name="mail" /><div><strong>Connect Gmail to send</strong><p>Connect a Gmail account securely. Tokens stay on the backend.</p><button type="button" className="primary-button" onClick={onConnectGmail} disabled={gmailLoading}>{gmailLoading ? "Connecting..." : <>Connect Gmail <Icon name="arrow" /></>}</button></div></> : canSend ? <><Icon name="shield" /><div><strong>{sending ? "Sending email..." : "Ready for your approval"}</strong><p>{sending ? "Gmail is sending the approved message. Please wait." : "AI review passed. Your explicit click will approve and send the edited email."}</p><div className="approval-actions"><button type="button" className="primary-button" onClick={onApprove} disabled={sending}>{sending ? <><span className="spinner" /> Sending...</> : <>Approve &amp; send email <Icon name="send" /></>}</button><button type="button" className="secondary-button" onClick={onReconnectGmail} disabled={gmailLoading || sending}>Reconnect Gmail</button></div></div></> : <><Icon name="alert" /><div><strong>Sending unavailable</strong><p>This draft must pass AI review and contain a non-empty email before sending.</p></div></>}</div></ResultCard>
    </div>
  </section>;
}

// Kept for compatibility with saved drafts created by the previous renderer.
// eslint-disable-next-line no-unused-vars
function ResultsLegacy({ result, humanApproved, onApprove, onNew, compact = false }) {
  const signals = result.signals?.signals || [];
  const sources = result.research?.sources || [];
  const review = result.review || {};
  const canApprove = Boolean(review.approved && result.email?.email_body?.trim() && result.history_id && !humanApproved);
  const copyEmail = async () => { if (result.email?.email_body) await navigator.clipboard?.writeText(result.email.email_body); };
  return <section className={`results-section ${compact ? "results-compact" : ""}`}><div className="results-heading"><div><p className="eyebrow-dark">Campaign review</p><h2>{result.email?.subject || "Outreach draft"}</h2></div>{!compact && <button type="button" className="secondary-button" onClick={onNew}><Icon name="plus" /> New campaign</button>}</div><div className="results-grid"><ResultCard number="01" title="Research summary" icon="search"><div className="summary-stats"><div><strong>{result.research?.total_sources || 0}</strong><span>Sources found</span></div><div><strong>{signals.length}</strong><span>Signals selected</span></div></div><p className="muted">Research for <strong>{result.research?.prospect?.name}</strong>, {result.research?.prospect?.company}.</p><div className="source-list">{sources.slice(0, 6).map((source, index) => <a key={source.url || index} href={source.url} target="_blank" rel="noreferrer"><Icon name="link" /><span>{source.title || source.url}</span><Icon name="external" /></a>)}{!sources.length && <p className="empty-inline">No research sources were found.</p>}</div></ResultCard><ResultCard number="02" title="Business signals" icon="pulse"><p className="muted">{result.signals?.overall_assessment || "Signals identified from the available research."}</p>{signals.length ? <div className="signal-list">{signals.map((signal, index) => <div className="signal-card" key={signal.source_url || index}><div className="signal-title"><h3>{signal.title}</h3><span className="confidence">{signal.confidence || "Evidence"}</span></div><p>{signal.summary}</p><dl><div><dt>Why it matters</dt><dd>{signal.relevance_reason}</dd></div><div><dt>Opportunity</dt><dd>{signal.business_opportunity}</dd></div></dl>{signal.source_url && <a href={signal.source_url} target="_blank" rel="noreferrer" className="inline-link">View source <Icon name="external" /></a>}</div>)}</div> : <EmptyState icon="pulse" title="No relevant signals" description="The evidence was not strong enough to support a safe personalized pitch." />}</ResultCard><ResultCard number="03" title="Generated email" icon="mail"><div className="email-meta"><span>Subject</span><strong>{result.email?.subject || "No subject generated"}</strong></div><div className="email-body">{result.email?.email_body || result.email?.reasoning || "No email was generated."}</div><div className="email-footer"><span><Icon name="link" /> {result.email?.personalization_signal || "No personalization signal"}</span><button type="button" className="secondary-button small-button" onClick={copyEmail}><Icon name="copy" /> Copy email</button></div></ResultCard><ResultCard number="04" title="AI quality review" icon="check"><div className="review-overview"><div className={`review-score ${review.approved ? "pass" : "fail"}`}><strong>{review.quality_score ?? 0}</strong><span>/ 100</span></div><div><StatusBadge status={review.approved ? "approved" : "rejected"} /><p>{review.review_summary}</p></div></div><div className="check-grid"><ReviewCheck label="Factual accuracy" value={review.factual_accuracy} /><ReviewCheck label="Product accuracy" value={review.product_accuracy} /><ReviewCheck label="Personalization" value={review.personalization} /><ReviewCheck label="Professionalism" value={review.professionalism} /></div>{review.issues?.length > 0 && <ReviewList title="Issues to address" items={review.issues} tone="danger" />}{review.suggestions?.length > 0 && <ReviewList title="Suggestions" items={review.suggestions} />}</ResultCard><ResultCard number="05" title="Human approval" icon="user"><div className={`approval-card ${humanApproved ? "approved" : ""}`}>{humanApproved ? <><Icon name="check" /><div><strong>Draft approved by you</strong><p>No email has been sent. Approval records your decision for this campaign.</p></div></> : canApprove ? <><Icon name="shield" /><div><strong>Review the evidence before approval</strong><p>The AI review passed. Your approval is required before this draft can move forward.</p><button type="button" className="primary-button" onClick={onApprove}>Approve this draft <Icon name="check" /></button></div></> : <><Icon name="alert" /><div><strong>Approval unavailable</strong><p>This draft must have a passing review and a non-empty email before it can be approved.</p></div></>}</div></ResultCard></div></section>;
}

function PageHeader({ eyebrow, title, description, action }) { return <header className="page-header"><div><p className="eyebrow-dark">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>{action}</header>; }
function MetricCard({ label, value, icon, tone }) { return <div className="metric-card"><div className={`metric-icon ${tone}`}><Icon name={icon} /></div><div><span>{label}</span><strong>{value}</strong></div></div>; }
function CampaignRow({ campaign, onOpen }) { return <button type="button" className="activity-row" onClick={() => onOpen(campaign.id)}><span className="activity-avatar">{campaign.prospect_name?.charAt(0) || "?"}</span><span className="activity-info"><strong>{campaign.prospect_name}</strong><small>{campaign.company} · {campaign.email_subject || "Untitled draft"}</small></span><span className="activity-date">{formatDate(campaign.generated_at)}<StatusBadge status={campaign.status || campaign.approval_status} /></span><Icon name="arrow" /></button>; }
function WorkflowStep({ number, title, text }) { return <div className="workflow-step"><span>{number}</span><div><strong>{title}</strong><p>{text}</p></div></div>; }
function FormSection({ title, description, icon, children }) { return <div className="form-section"><div className="form-section-heading"><span className="section-icon"><Icon name={icon} /></span><div><h3>{title}</h3><p>{description}</p></div></div><div className="form-grid">{children}</div></div>; }
function Input({ label, name, type = "text", placeholder, value, onChange, required = true }) { return <label className="field"><span>{label}{required && <em>*</em>}</span><input type={type} name={name} placeholder={placeholder} value={value} onChange={onChange} required={required} /></label>; }
function ResultCard({ number, title, icon, children }) { return <article className="result-card"><div className="result-card-heading"><span className="result-number">{number}</span><span className="section-icon"><Icon name={icon} /></span><h3>{title}</h3></div>{children}</article>; }
function ReviewCheck({ label, value }) { const passed = value === "Pass"; return <div className="review-check"><span className={passed ? "check-pass" : "check-fail"}><Icon name={passed ? "check" : "close"} /></span><div><span>{label}</span><strong>{value || "Not checked"}</strong></div></div>; }
function ReviewList({ title, items, tone = "" }) { return <div className={`review-list ${tone}`}><strong>{title}</strong><ul>{items.map((item, index) => <li key={index}>{item}</li>)}</ul></div>; }
function StatusBadge({ status }) { const labels = { approved: "Approved", rejected: "Needs review", awaiting_approval: "Awaiting approval", ai_review_failed: "Review failed", sent: "Sent", failed: "Failed", replied: "Replied", pending: "Awaiting review" }; const className = status === "rejected" ? "ai_review_failed" : status || "pending"; return <span className={`status-badge ${className}`}>{labels[status] || "Awaiting review"}</span>; }
function LoadingState({ label }) { return <div className="loading-state"><span className="spinner spinner-dark" />{label}</div>; }
function EmptyState({ icon, title, description, action }) { return <div className="empty-state"><span className="empty-icon"><Icon name={icon} /></span><h3>{title}</h3><p>{description}</p>{action}</div>; }
function formatDate(value) { if (!value) return "—"; return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(value)); }

function Icon({ name }) {
  const paths = { grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>, plus: <><path d="M12 5v14M5 12h14" /></>, clock: <><circle cx="12" cy="12" r="8.5" /><path d="M12 7v5l3 2" /></>, spark: <><path d="m12 3 1.5 6.5L20 12l-6.5 1.5L12 20l-1.5-6.5L4 12l6.5-2.5L12 3Z" /></>, menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>, arrow: <><path d="M5 12h14M13 6l6 6-6 6" /></>, send: <><path d="m21 3-7.5 18-3.2-7.3L3 10.5 21 3Z" /><path d="m10.3 13.7 4.2-4.2" /></>, check: <><path d="m5 12 4 4L19 6" /></>, link: <><path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1" /><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 7 20l1.1-1.1" /></>, user: <><circle cx="12" cy="8" r="3" /><path d="M5 20a7 7 0 0 1 14 0" /></>, briefcase: <><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M8 7V5h8v2M3 12h18" /></>, shield: <><path d="M12 3 19 6v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3Z" /><path d="m9 12 2 2 4-4" /></>, alert: <><path d="M12 4 21 20H3L12 4Z" /><path d="M12 10v4M12 17h.01" /></>, search: <><circle cx="10.8" cy="10.8" r="6.8" /><path d="m16 16 4.5 4.5" /></>, pulse: <><path d="M3 12h4l2-6 4 12 2-6h6" /></>, mail: <><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" /></>, copy: <><rect x="8" y="8" width="11" height="11" rx="2" /><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" /></>, external: <><path d="M14 5h5v5M19 5l-8 8" /><path d="M18 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>, trash: <><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" /></>, close: <><path d="m6 6 12 12M18 6 6 18" /></> };
  return <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.grid}</svg>;
}

export default App;
