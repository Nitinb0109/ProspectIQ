
import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [form, setForm] = useState({
    prospectName: "",
    designation: "",
    company: "",
    website: "",
    senderCompany: "",
    product: "",
    valueProposition: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [humanApproved, setHumanApproved] = useState(false);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setLoading(true);
    setError("");
    setResult(null);
    setHumanApproved(false);

    // Convert frontend field names to backend field names
    const requestData = {
      prospect_name: form.prospectName,
      designation: form.designation,
      company: form.company,
      company_website: form.website || null,
      sender_company: form.senderCompany,
      product_or_service: form.product,
      value_proposition: form.valueProposition,
    };

    try {
      const response = await fetch(`${API_URL}/api/outreach/generate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Something went wrong while generating outreach."
        );
      }

      setResult(data);
    } catch (err) {
      setError(
        err.message ||
          "Unable to connect to the backend. Check whether FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const signals = result?.signals?.signals || [];
  const sources = result?.research?.sources || [];
  const review = result?.review;
  const canHumanApprove = Boolean(
    review?.approved &&
    result?.email?.email_body?.trim()
  );

  return (
    <div className="app">
      <aside className="sidebar">
        <h2>⚡ ProspectIQ</h2>
        <p className="menu-label">WORKSPACE</p>
        <div className="menu-item active">▦ Dashboard</div>
        <div className="menu-item">✉ New Outreach</div>
        <div className="menu-item">◷ History</div>

        <div className="sidebar-bottom">
          <div className="menu-item">⚙ Settings</div>
          <p>AI-powered B2B outreach</p>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <h3>Dashboard</h3>
            <p>Welcome to your personalised outreach workspace.</p>
          </div>
          <div className="status">● API connected locally</div>
        </header>

        <section className="hero">
          <div>
            <span className="eyebrow">AI-POWERED OUTREACH</span>
            <h1>
              Turn prospects into
              <br />
              meaningful conversations.
            </h1>
            <p>
              Research real business signals and create personalised emails
              in minutes.
            </p>
          </div>
          <div className="hero-icon">✦</div>
        </section>

        <section className="stats">
          <div className="stat-card">
            <span>Research sources</span>
            <h2>{result ? sources.length : "—"}</h2>
            <small>{result ? "Sources collected" : "Awaiting research"}</small>
          </div>

          <div className="stat-card">
            <span>Signals discovered</span>
            <h2>{result ? signals.length : "—"}</h2>
            <small>{result ? "Signals identified" : "Awaiting analysis"}</small>
          </div>

          <div className="stat-card">
            <span>Review score</span>
            <h2>{review ? `${review.quality_score}/100` : "—"}</h2>
            <small>{review ? "AI quality review" : "Awaiting review"}</small>
          </div>
        </section>

        <section className="form-card">
          <div className="section-heading">
            <div>
              <h2>Start new outreach</h2>
              <p>Enter the prospect and your product details.</p>
            </div>
            <span className="step">STEP 01</span>
          </div>

          <form onSubmit={handleSubmit}>
            <h3>Prospect information</h3>

            <div className="form-grid">
              <Input label="Prospect name" name="prospectName"
                placeholder="e.g. Satya Nadella"
                value={form.prospectName} onChange={handleChange} />

              <Input label="Designation" name="designation"
                placeholder="e.g. CEO"
                value={form.designation} onChange={handleChange} />

              <Input label="Company" name="company"
                placeholder="e.g. Microsoft"
                value={form.company} onChange={handleChange} />

              <Input label="Company website (optional)" name="website"
                placeholder="https://example.com"
                value={form.website} onChange={handleChange}
                required={false} />
            </div>

            <div className="form-divider" />

            <h3>Your offering</h3>

            <div className="form-grid">
              <Input label="Your company" name="senderCompany"
                placeholder="Your company name"
                value={form.senderCompany} onChange={handleChange} />

              <Input label="Product / Service" name="product"
                placeholder="What do you offer?"
                value={form.product} onChange={handleChange} />
            </div>

            <label className="field full-field">
              <span>Value proposition</span>
              <textarea
                name="valueProposition"
                value={form.valueProposition}
                onChange={handleChange}
                placeholder="Explain how your product helps the prospect..."
                required
                rows="3"
              />
            </label>

            <button type="submit" className="submit-btn" disabled={loading}>
              {loading
                ? "Researching prospect and generating email..."
                : "Generate personalised outreach →"}
            </button>
          </form>

          {loading && (
            <p className="loading-message">
              Please wait. ProspectIQ is researching sources, analysing
              signals, writing your email and reviewing its quality.
            </p>
          )}

          {error && (
            <div className="error-box">
              <strong>Error:</strong> {error}
            </div>
          )}
        </section>

        {result && (
          <section className="results-section">
            <h2>Outreach results</h2>

            <div className="result-card">
              <h3>1. Research summary</h3>
              <p>
                Prospect: <strong>{result.research?.prospect?.name}</strong>
              </p>
              <p>
                Company: <strong>{result.research?.prospect?.company}</strong>
              </p>
              <p>Total sources found: {result.research?.total_sources || 0}</p>

              {sources.length > 0 ? (
                <ul>
                  {sources.map((source, index) => (
                    <li key={source.url || index}>
                      <a href={source.url} target="_blank" rel="noreferrer">
                        {source.title || source.url}
                      </a>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No research sources were found.</p>
              )}
            </div>

            <div className="result-card">
              <h3>2. Identified business signals</h3>

              {signals.length > 0 ? (
                signals.map((signal, index) => (
                  <div className="signal-item" key={index}>
                    <h4>{signal.title}</h4>
                    <p>{signal.summary}</p>
                    <p>
                      <strong>Relevance:</strong> {signal.relevance_reason}
                    </p>
                    <p>
                      <strong>Opportunity:</strong> {signal.business_opportunity}
                    </p>
                    <p>
                      <strong>Confidence:</strong> {signal.confidence}
                    </p>
                    {signal.source_url && (
                      <a href={signal.source_url} target="_blank" rel="noreferrer">
                        View source
                      </a>
                    )}
                  </div>
                ))
              ) : (
                <p>No relevant signals identified. Do not assume a signal exists.</p>
              )}

              <p>
                <strong>Overall assessment:</strong>{" "}
                {result.signals?.overall_assessment || "Not available"}
              </p>
            </div>

            <div className="result-card">
              <h3>3. Generated email</h3>

              <p>
                <strong>Subject:</strong> {result.email?.subject}
              </p>

              <div className="email-body">
                {result.email?.email_body}
              </div>

              <p>
                <strong>Personalization signal:</strong>{" "}
                {result.email?.personalization_signal}
              </p>

              <p>
                <strong>Reasoning:</strong> {result.email?.reasoning}
              </p>

              {result.email?.source_url && (
                <a href={result.email.source_url} target="_blank" rel="noreferrer">
                  Open personalization source
                </a>
              )}
            </div>

            <div className="result-card">
              <h3>4. AI quality review</h3>

              <h2>
                {review?.approved ? "AI review passed" : "AI review not approved"}
              </h2>

              <p>
                Quality score: <strong>{review?.quality_score}/100</strong>
              </p>

              <p>{review?.review_summary}</p>

              <h4>Review checks</h4>
              <ul>
                <li>Factual accuracy: {review?.factual_accuracy}</li>
                <li>Product accuracy: {review?.product_accuracy}</li>
                <li>Personalization: {review?.personalization}</li>
                <li>Professionalism: {review?.professionalism}</li>
              </ul>

              {review?.issues?.length > 0 && (
                <>
                  <h4>Issues identified</h4>
                  <ul>
                    {review.issues.map((issue, index) => (
                      <li key={index}>{issue}</li>
                    ))}
                  </ul>
                </>
              )}

              {review?.suggestions?.length > 0 && (
                <>
                  <h4>Suggestions</h4>
                  <ul>
                    {review.suggestions.map((suggestion, index) => (
                      <li key={index}>{suggestion}</li>
                    ))}
                  </ul>
                </>
              )}

              
<div className="approval-area">
  {humanApproved ? (
    <p className="approved-message">
      You have approved this draft for the next step.
      No email has been sent.
    </p>
  ) : canHumanApprove ? (
    <>
      <p>
        The AI review passed. Please check the research
        evidence and email before giving your approval.
      </p>

      <button
        type="button"
        className="approve-btn"
        onClick={() => setHumanApproved(true)}
      >
        I have reviewed and approve this draft
      </button>
    </>
  ) : (
    <div className="error-box">
      <strong>Human approval unavailable.</strong>
      <p>
        This draft has not passed AI review, or the
        generated email is empty. Resolve the issues
        before proceeding.
      </p>
    </div>
  )}
</div>

            </div>
          </section>
        )}

        <footer>
          © 2026 ProspectIQ · Personalised outreach powered by AI
        </footer>
      </main>
    </div>
  );
}

function Input({
  label,
  name,
  placeholder,
  value,
  onChange,
  required = true,
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        name={name}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        required={required}
      />
    </label>
  );
}

export default App;
