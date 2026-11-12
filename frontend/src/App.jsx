
import { useState } from "react";
import "./App.css";

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

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    alert("Prospect details submitted! Backend integration coming next.");
    console.log(form);
  };

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
          <div className="status">● System ready</div>
        </header>

        <section className="hero">
          <div>
            <span className="eyebrow">AI-POWERED OUTREACH</span>
            <h1>Turn prospects into<br />meaningful conversations.</h1>
            <p>Research real business signals and create personalised emails in minutes.</p>
          </div>
          <div className="hero-icon">✦</div>
        </section>

        <section className="stats">
          <div className="stat-card">
            <span>Total prospects</span>
            <h2>—</h2>
            <small>Coming soon</small>
          </div>
          <div className="stat-card">
            <span>Signals discovered</span>
            <h2>—</h2>
            <small>Coming soon</small>
          </div>
          <div className="stat-card">
            <span>Emails generated</span>
            <h2>—</h2>
            <small>Coming soon</small>
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
              <Input label="Prospect name" name="prospectName" placeholder="e.g. Satya Nadella" value={form.prospectName} onChange={handleChange} />
              <Input label="Designation" name="designation" placeholder="e.g. CEO" value={form.designation} onChange={handleChange} />
              <Input label="Company" name="company" placeholder="e.g. Microsoft" value={form.company} onChange={handleChange} />
              <Input label="Company website" name="website" placeholder="https://example.com" value={form.website} onChange={handleChange} />
            </div>

            <div className="form-divider" />

            <h3>Your offering</h3>

            <div className="form-grid">
              <Input label="Your company" name="senderCompany" placeholder="Your company name" value={form.senderCompany} onChange={handleChange} />
              <Input label="Product / Service" name="product" placeholder="What do you offer?" value={form.product} onChange={handleChange} />
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

            <button type="submit" className="submit-btn">
              Generate personalised outreach →
            </button>
          </form>
        </section>

        <footer>© 2026 ProspectIQ · Personalised outreach powered by AI</footer>
      </main>
    </div>
  );
}

function Input({ label, name, placeholder, value, onChange }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input
        name={name}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        required
      />
    </label>
  );
}

export default App;
