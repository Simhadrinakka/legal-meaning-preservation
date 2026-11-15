import React, { useState } from 'react';
import { evaluateTextPair } from './api';

// Official statutory examples for interactive demonstration
const SAMPLE_PAIRS = {
  en: {
    original:
      "(1) Subject to such conditions as may be prescribed, any officer authorised by the Chief Registrar by a general or special order in this behalf may, either before or after the institution of criminal proceedings under this Act, accept from the person who has committed or is reasonably suspected of having committed an offence under this Act, by way of composition of such offence a sum of money not exceeding fifty rupees.",
    simplified:
      "(1) Subject to prescribed conditions, an officer authorized by the Chief Registrar by a general or special order may, either before or after criminal proceedings are initiated under this Act, accept up to fifty rupees to compound an offence from any person who has committed or is suspected of committing that offence.",
  },
  hi: {
    original:
      "धारा 24 की उपधारा (1) के अधीन किसी अपराध के शमन के लिए कोई भी धनराशि, जो पचास रुपये से अधिक न हो, ऐसे अधिकारी द्वारा स्वीकार की जा सकेगी जिसे मुख्य रजिस्ट्रार द्वारा साधारण या विशेष आदेश द्वारा इस निमित्त प्राधिकृत किया गया हो।",
    simplified:
      "धारा 24(1) के अधीन मुख्य रजिस्ट्रार द्वारा प्राधिकृत अधिकारी अपराध के शमन हेतु पचास रुपये तक की राशि स्वीकार कर सकेगा।",
  },
};

// User-friendly mappings for legal status and error categories
const DECISION_LABELS_MAP = {
  PRESERVED: 'Full Legal Preservation',
  MOSTLY_PRESERVED: 'Mostly Preserved (Minor Drift)',
  PARTIALLY_PRESERVED: 'Partially Preserved (Noticeable Drift)',
  MAJOR_LOSS: 'Major Legal Meaning Loss',
  FUNDAMENTALLY_ALTERED: 'Fundamentally Altered',
};

const ERROR_LABELS_MAP = {
  NONE: 'No Meaning Distortion Detected',
  OMISSION: 'Material Element Omitted',
  HALLUCINATION_ADDITION: 'Unauthorized Addition Introduced',
  CONTRADICTION: 'Statutory Contradiction / Liability Inversion',
  MODALITY_CHANGE: 'Deontic Modality Altered (Obligation vs Discretion)',
  CONDITION_EXCEPTION_LOSS: 'Condition or Exception Omitted',
  SCOPE_CHANGE: 'Jurisdictional or Applicability Scope Shift',
  NUMERIC_ENTITY_REFERENCE_ERROR: 'Numerical Threshold or Reference Altered',
};

// Helper: map numerical score to user-facing badge styling
function getScoreBadge(score) {
  if (score === null || score === undefined) {
    return { className: 'badge-default', label: 'Awaiting Assessment' };
  }
  if (score >= 9.0) return { className: 'badge-preserved', label: 'Preserved' };
  if (score >= 7.0) return { className: 'badge-mostly', label: 'Mostly Preserved' };
  if (score >= 5.0) return { className: 'badge-partial', label: 'Partially Preserved' };
  if (score >= 3.0) return { className: 'badge-major', label: 'Major Meaning Loss' };
  return { className: 'badge-critical', label: 'Fundamentally Altered' };
}

// Helper: format probability value as percentage
function formatProb(prob) {
  if (prob === undefined || prob === null) return null;
  return `${(prob * 100).toFixed(1)}%`;
}

export default function App() {
  const [language, setLanguage] = useState('en');
  const [originalText, setOriginalText] = useState('');
  const [simplifiedText, setSimplifiedText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [result, setResult] = useState(null);

  // Smooth scroll helper for intentional hero & navbar navigation
  const scrollToSection = (id) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Clear stale results on input edit
  const handleOriginalChange = (val) => {
    setOriginalText(val);
    setErrorMessage(null);
    setResult(null);
  };

  const handleSimplifiedChange = (val) => {
    setSimplifiedText(val);
    setErrorMessage(null);
    setResult(null);
  };

  // Load sample text pair for currently selected language
  const handleLoadSample = () => {
    const sample = SAMPLE_PAIRS[language];
    setOriginalText(sample.original);
    setSimplifiedText(sample.simplified);
    setErrorMessage(null);
    setResult(null);
  };

  // Switch language and clear stale output
  const handleLanguageChange = (lang) => {
    setLanguage(lang);
    setErrorMessage(null);
    setResult(null);
  };

  // Clear all text inputs and outputs
  const handleClear = () => {
    setOriginalText('');
    setSimplifiedText('');
    setErrorMessage(null);
    setResult(null);
  };

  // Execute evaluation via backend API (CRITICAL: Does NOT auto-scroll)
  const handleAnalyze = async () => {
    setErrorMessage(null);

    // Client-side empty validation
    if (!originalText.trim() || !simplifiedText.trim()) {
      setErrorMessage('Both Original Legal Text and Simplified Legal Text are required.');
      return;
    }

    setIsLoading(true);

    try {
      const data = await evaluateTextPair({
        originalText,
        simplifiedText,
        language,
      });
      setResult(data);
      setErrorMessage(null);
      // NOTE: User stays at their current scroll position; results update below.
    } catch (err) {
      setErrorMessage(
        err.message || 'An unexpected error occurred while communicating with the backend.'
      );
      setResult(null);
    } finally {
      setIsLoading(false);
    }
  };

  // Extract structured prediction & explanation data
  const prediction = result?.prediction;
  const explanation = result?.explanation;

  const score =
    prediction?.lmp_score !== undefined
      ? prediction.lmp_score
      : explanation?.predicted_score !== undefined
      ? explanation.predicted_score
      : null;

  const decision =
    prediction?.pred_decision ||
    prediction?.decision ||
    explanation?.predicted_decision ||
    null;

  const errorType =
    prediction?.pred_error ||
    prediction?.error_type ||
    explanation?.predicted_error ||
    null;

  const decisionProbs =
    prediction?.decision_probabilities ||
    explanation?.hybrid_prediction?.decision_probabilities ||
    {};
  const errorProbs =
    prediction?.error_probabilities ||
    explanation?.hybrid_prediction?.error_probabilities ||
    {};

  const topDecisionProb =
    decision && decisionProbs[decision] !== undefined
      ? decisionProbs[decision]
      : null;
  const topErrorProb =
    errorType && errorProbs[errorType] !== undefined
      ? errorProbs[errorType]
      : null;

  const scoreBadge = getScoreBadge(score);

  // Invariant shift lists
  const invariantShifts = explanation?.detected_invariant_shifts || {};
  const modalShifts = invariantShifts.modal_shifts || [];
  const negationShifts = invariantShifts.negation_prohibition_shifts || [];
  const conditionShifts = invariantShifts.condition_exception_shifts || [];
  const numericalShifts = invariantShifts.numerical_reference_shifts || [];
  const scopeShifts = invariantShifts.scope_shifts || [];
  const penalShifts = invariantShifts.penal_sanction_shifts || [];
  const hasProhibitionOrPenalShift =
    negationShifts.length > 0 || penalShifts.length > 0;
  const prohibitionDetail =
    negationShifts[0]?.details ||
    penalShifts[0]?.details ||
    "No statutory prohibitions removed; no unauthorized penal additions detected.";

  // Differences
  const textDiffs = explanation?.text_differences || {};
  const omittedSegments = textDiffs.omitted_segments || [];
  const addedSegments = textDiffs.added_segments || [];

  return (
    <div className="site-wrapper">
      {/* =====================================================================
          1. STICKY NAVBAR
          ===================================================================== */}
      <header className="site-navbar">
        <div className="navbar-container">
          <div className="navbar-brand" onClick={() => scrollToSection('home')}>
            <div className="brand-icon-wrapper">
              <svg
                className="brand-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
                <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
                <path d="M7 21h10" />
                <path d="M12 3v18" />
                <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" />
              </svg>
            </div>
            <div className="brand-text">
              <span className="brand-name">JUDGEBERT</span>
              <span className="brand-tagline">Legal Meaning Preservation</span>
            </div>
          </div>

          <nav className="navbar-nav">
            <button
              type="button"
              className="nav-link"
              onClick={() => scrollToSection('home')}
            >
              Home
            </button>
            <button
              type="button"
              className="nav-link"
              onClick={() => scrollToSection('how-it-works')}
            >
              How It Works
            </button>
            <button
              type="button"
              className="nav-link"
              onClick={() => scrollToSection('compare')}
            >
              Analyze Text
            </button>
            <button
              type="button"
              className="btn-nav-cta"
              onClick={() => scrollToSection('compare')}
            >
              <span>Start Analysis</span>
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
          </nav>
        </div>
      </header>

      <main className="main-content">
        {/* =====================================================================
            2. HERO SECTION
            ===================================================================== */}
        <section className="hero-section" id="home">
          <div className="hero-container">
            <div className="hero-badge">
              <span className="hero-badge-dot"></span>
              <span>Statutory Meaning Verification Platform</span>
            </div>

            <h1 className="hero-title">
              Understand Legal Meaning.{' '}
              <span className="hero-title-accent">Preserve What Matters.</span>
            </h1>

            <p className="hero-subtitle">
              Evaluate whether simplified legal text preserves the meaning of the
              original English or Hindi statute.
            </p>

            <div className="hero-actions">
              <button
                type="button"
                className="btn-hero-primary"
                onClick={() => scrollToSection('compare')}
              >
                <span>Start Analysis</span>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </button>

              <button
                type="button"
                className="btn-hero-secondary"
                onClick={() => scrollToSection('how-it-works')}
              >
                <span>How It Works</span>
              </button>
            </div>

            {/* Feature Highlights Strip */}
            <div className="hero-highlights">
              <div className="highlight-item">
                <span className="highlight-icon">🌐</span>
                <span>English &amp; हिन्दी (Hindi)</span>
              </div>
              <div className="highlight-dot">&bull;</div>
              <div className="highlight-item">
                <span className="highlight-icon">⚖️</span>
                <span>Deontic Modality Verification</span>
              </div>
              <div className="highlight-dot">&bull;</div>
              <div className="highlight-item">
                <span className="highlight-icon">🛡️</span>
                <span>Statutory Invariant Protection</span>
              </div>
            </div>
          </div>
        </section>

        {/* =====================================================================
            3. HOW IT WORKS SECTION
            ===================================================================== */}
        <section className="how-it-works-section" id="how-it-works">
          <div className="section-header-centered">
            <span className="section-pill">Workflow</span>
            <h2 className="section-heading-lg">How It Works</h2>
            <p className="section-subheading">
              Three simple steps to evaluate plain-language statutory simplifications with legal certainty.
            </p>
          </div>

          <div className="steps-grid">
            <div className="step-card">
              <div className="step-number">01</div>
              <h3 className="step-title">Input Statutory Text</h3>
              <p className="step-desc">
                Select English or Hindi, then provide the original statute and the simplified candidate text.
              </p>
            </div>

            <div className="step-card">
              <div className="step-number">02</div>
              <h3 className="step-title">Verify Legal Invariants</h3>
              <p className="step-desc">
                The engine evaluates obligations, conditions, prohibitions, numbers, and institutional scope.
              </p>
            </div>

            <div className="step-card">
              <div className="step-number">03</div>
              <h3 className="step-title">Review Meaning Assessment</h3>
              <p className="step-desc">
                Receive an objective 1–10 preservation score, status classification, and detailed discrepancy highlights.
              </p>
            </div>
          </div>
        </section>

        {/* =====================================================================
            4. TEXT COMPARISON SECTION
            ===================================================================== */}
        <section className="compare-section" id="compare">
          <div className="section-header-clean">
            <div>
              <h2 className="section-heading">Compare Legal Texts</h2>
              <p className="section-subheading">
                Input statutory source text and plain-language candidate to evaluate semantic and legal fidelity.
              </p>
            </div>
          </div>

          {/* Toolbar: Language Switcher and Quick Actions */}
          <div className="compare-toolbar">
            <div className="lang-toggle-group">
              <span className="toolbar-label">Language:</span>
              <div className="segmented-control">
                <button
                  type="button"
                  className={`segmented-btn ${language === 'en' ? 'active' : ''}`}
                  onClick={() => handleLanguageChange('en')}
                  disabled={isLoading}
                >
                  English
                </button>
                <button
                  type="button"
                  className={`segmented-btn ${language === 'hi' ? 'active' : ''}`}
                  onClick={() => handleLanguageChange('hi')}
                  disabled={isLoading}
                >
                  हिन्दी (Hindi)
                </button>
              </div>
            </div>

            <div className="toolbar-actions">
              <button
                type="button"
                className="btn-toolbar-secondary"
                onClick={handleLoadSample}
                disabled={isLoading}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z" />
                </svg>
                <span>Load Sample</span>
              </button>

              <button
                type="button"
                className="btn-toolbar-ghost"
                onClick={handleClear}
                disabled={isLoading}
              >
                <span>Clear</span>
              </button>
            </div>
          </div>

          {/* Validation Error Banner */}
          {errorMessage && (
            <div className="saas-alert-banner" role="alert">
              <svg
                className="alert-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <div className="alert-content">
                <strong>Validation Notice:</strong> {errorMessage}
              </div>
            </div>
          )}

          {/* Side-by-Side Input Panels */}
          <div className="input-panels-grid">
            {/* Panel A: Original Legal Text */}
            <div className="input-panel-card">
              <div className="panel-header">
                <div className="panel-title-group">
                  <span className="panel-label">Original Legal Text</span>
                  <span className="panel-tag source">Statute / Source</span>
                </div>
                <span className="char-count">{originalText.length} characters</span>
              </div>
              <textarea
                className="saas-textarea"
                value={originalText}
                onChange={(e) => handleOriginalChange(e.target.value)}
                disabled={isLoading}
                placeholder={
                  language === 'en'
                    ? "Paste original English statutory text (e.g. section from Act with obligations, conditions, and penalties)..."
                    : "मूल हिन्दी विधिक पाठ यहाँ दर्ज करें (उदा. अधिनियम की धारा, शर्तें, उपबंध या शास्तियां)..."
                }
              />
              <div className="panel-footer-hint">
                Contains statutory anchors: mandatory obligations (shall/must), conditions, and penalties.
              </div>
            </div>

            {/* Panel B: Simplified Legal Text */}
            <div className="input-panel-card">
              <div className="panel-header">
                <div className="panel-title-group">
                  <span className="panel-label">Simplified Legal Text</span>
                  <span className="panel-tag candidate">Plain Language</span>
                </div>
                <span className="char-count">{simplifiedText.length} characters</span>
              </div>
              <textarea
                className="saas-textarea"
                value={simplifiedText}
                onChange={(e) => handleSimplifiedChange(e.target.value)}
                disabled={isLoading}
                placeholder={
                  language === 'en'
                    ? "Paste simplified English candidate text to evaluate legal fidelity..."
                    : "सरलीकृत हिन्दी पाठ यहाँ दर्ज करें जिसकी विधिक अर्थ-संरक्षण क्षमता जांचनी है..."
                }
              />
              <div className="panel-footer-hint">
                Evaluated for fidelity, omissions, introduced duties, and modal force.
              </div>
            </div>
          </div>

          {/* Action Row: Prominent Button (Does NOT auto-scroll) */}
          <div className="compare-action-row">
            <button
              type="button"
              className="btn-analyze"
              onClick={handleAnalyze}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="saas-spinner"></span>
                  <span>Analyzing Legal Meaning...</span>
                </>
              ) : (
                <>
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
                    <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
                    <path d="M7 21h10" />
                    <path d="M12 3v18" />
                    <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" />
                  </svg>
                  <span>Analyze Legal Meaning</span>
                </>
              )}
            </button>

            {result && (
              <div className="latency-indicator">
                <span>⚡ Analysis completed in {result.latency_ms}ms</span>
              </div>
            )}
          </div>
        </section>

        {/* =====================================================================
            5. RESULTS SECTION: LEGAL MEANING ASSESSMENT
            ===================================================================== */}
        {result && (
          <section className="assessment-section" id="results">
            <div className="section-header-clean">
              <div>
                <h2 className="section-heading">Legal Meaning Assessment</h2>
                <p className="section-subheading">
                  Assessment of semantic fidelity and statutory invariant preservation.
                </p>
              </div>
            </div>

            {/* Outcome Banner: Success State vs Meaning Distortion Warning */}
            {score >= 9.0 ? (
              <div className="outcome-banner success">
                <div className="outcome-icon-circle success">
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <div className="outcome-content">
                  <div className="outcome-title">Full Legal Meaning Preserved</div>
                  <p className="outcome-desc">
                    {explanation?.human_readable_summary ||
                      'The plain-language candidate text faithfully preserves all statutory rights, duties, conditions, and penalties.'}
                  </p>
                </div>
              </div>
            ) : (
              <div className="outcome-banner warning">
                <div className="outcome-icon-circle warning">
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                    <line x1="12" y1="9" x2="12" y2="13" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                </div>
                <div className="outcome-content">
                  <div className="outcome-title">Meaning Distortion Detected</div>
                  <p className="outcome-desc">
                    {explanation?.human_readable_summary ||
                      'The simplified text alters statutory rights, obligations, or preconditions. Review required.'}
                  </p>
                </div>
              </div>
            )}

            {/* 3 Main Metric Cards */}
            <div className="assessment-grid">
              {/* Card 1: Legal Preservation Score */}
              <div className="assessment-card">
                <div className="assessment-card-header">
                  <span className="card-label">Legal Preservation Score</span>
                  <span className="card-tag">1–10 Scale</span>
                </div>
                <div className="score-display">
                  <span className="score-number">
                    {score !== null ? score.toFixed(2) : '--'}
                  </span>
                  <span className="score-denom">/ 10.0</span>
                </div>
                <div className={`status-pill ${scoreBadge.className}`}>
                  {scoreBadge.label}
                </div>
                <p className="card-explanation">
                  {explanation?.score_band_explanation ||
                    'Continuous assessment calibrated to official legal scoring rubrics.'}
                </p>
              </div>

              {/* Card 2: Preservation Status */}
              <div className="assessment-card">
                <div className="assessment-card-header">
                  <span className="card-label">Preservation Status</span>
                  <span className="card-tag">Classification</span>
                </div>
                <div className="status-display">
                  <span className="status-text">
                    {decision
                      ? DECISION_LABELS_MAP[decision] || decision
                      : 'Pending Evaluation'}
                  </span>
                </div>
                {topDecisionProb !== null && (
                  <div className="confidence-wrapper">
                    <div className="confidence-header">
                      <span>Confidence</span>
                      <span>{formatProb(topDecisionProb)}</span>
                    </div>
                    <div className="confidence-track">
                      <div
                        className="confidence-fill"
                        style={{ width: `${topDecisionProb * 100}%` }}
                      ></div>
                    </div>
                  </div>
                )}
                <p className="card-explanation">
                  {decision === 'PRESERVED'
                    ? 'All statutory rights, duties, conditions, and penalties remain intact.'
                    : 'Categorical determination of whether statutory force has been diluted or altered.'}
                </p>
              </div>

              {/* Card 3: Detected Meaning Changes */}
              <div className="assessment-card">
                <div className="assessment-card-header">
                  <span className="card-label">Detected Meaning Changes</span>
                  <span className="card-tag">Discrepancy</span>
                </div>
                <div className="status-display">
                  <span
                    className={`error-text ${errorType === 'NONE' ? 'safe' : 'alert'}`}
                  >
                    {errorType
                      ? ERROR_LABELS_MAP[errorType] || errorType
                      : 'Pending Evaluation'}
                  </span>
                </div>
                {topErrorProb !== null && (
                  <div className="confidence-wrapper">
                    <div className="confidence-header">
                      <span>Category Match</span>
                      <span>{formatProb(topErrorProb)}</span>
                    </div>
                    <div className="confidence-track">
                      <div
                        className="confidence-fill"
                        style={{
                          width: `${topErrorProb * 100}%`,
                          backgroundColor:
                            errorType === 'NONE' ? '#16a34a' : '#ea580c',
                        }}
                      ></div>
                    </div>
                  </div>
                )}
                <p className="card-explanation">
                  {explanation?.error_explanation ||
                    'Identifies specific statutory shifts: modality change, condition loss, scope distortion, or numerical error.'}
                </p>
              </div>
            </div>

            {/* Statutory Safeguards & Invariant Checks */}
            <div className="safeguards-section">
              <div className="safeguards-header">
                <h3 className="subsection-title">Statutory Safeguards &amp; Invariant Checks</h3>
                <p className="subsection-desc">
                  Verification across 5 foundational dimensions of statutory drafting.
                </p>
              </div>

              <div className="safeguards-grid">
                {/* Safeguard 1: Deontic Modality */}
                <div className="safeguard-card">
                  <div className="safeguard-top">
                    <span className="safeguard-icon">📌</span>
                    <span className="safeguard-title">Deontic Modality</span>
                  </div>
                  <span
                    className={`safeguard-badge ${
                      modalShifts.length > 0 ? 'alert' : 'safe'
                    }`}
                  >
                    {modalShifts.length > 0 ? '⚠️ Modal Shift' : '✓ Modality Intact'}
                  </span>
                  <p className="safeguard-detail">
                    {modalShifts.length > 0
                      ? modalShifts[0].details
                      : "Preserves mandatory ('shall'/'होगा') and discretionary ('may'/'सकेगा') force."}
                  </p>
                </div>

                {/* Safeguard 2: Prohibitions & Liabilities */}
                <div className="safeguard-card">
                  <div className="safeguard-top">
                    <span className="safeguard-icon">🚫</span>
                    <span className="safeguard-title">Prohibitions &amp; Liabilities</span>
                  </div>
                  <span
                    className={`safeguard-badge ${
                      hasProhibitionOrPenalShift ? 'alert' : 'safe'
                    }`}
                  >
                    {hasProhibitionOrPenalShift ? '⚠️ Prohibition Altered' : '✓ No Inversion'}
                  </span>
                  <p className="safeguard-detail">
                    {hasProhibitionOrPenalShift
                      ? prohibitionDetail
                      : "No statutory prohibitions removed; no unauthorized penal additions detected."}
                  </p>
                </div>

                {/* Safeguard 3: Conditions & Exceptions */}
                <div className="safeguard-card">
                  <div className="safeguard-top">
                    <span className="safeguard-icon">⚖️</span>
                    <span className="safeguard-title">Conditions &amp; Exceptions</span>
                  </div>
                  <span
                    className={`safeguard-badge ${
                      conditionShifts.length > 0 ? 'alert' : 'safe'
                    }`}
                  >
                    {conditionShifts.length > 0
                      ? '⚠️ Condition Altered'
                      : '✓ Conditions Preserved'}
                  </span>
                  <p className="safeguard-detail">
                    {conditionShifts.length > 0
                      ? conditionShifts[0].details
                      : "Statutory preconditions ('subject to', 'provided that', 'के अधीन') and exceptions preserved."}
                  </p>
                </div>

                {/* Safeguard 4: Numbers & Citations */}
                <div className="safeguard-card">
                  <div className="safeguard-top">
                    <span className="safeguard-icon">🔢</span>
                    <span className="safeguard-title">Numbers &amp; Citations</span>
                  </div>
                  <span
                    className={`safeguard-badge ${
                      numericalShifts.length > 0 ? 'alert' : 'safe'
                    }`}
                  >
                    {numericalShifts.length > 0 ? '⚠️ Figures Altered' : '✓ Figures Match'}
                  </span>
                  <p className="safeguard-detail">
                    {numericalShifts.length > 0
                      ? numericalShifts[0].details
                      : 'Numerical caps, fine amounts, terms of imprisonment, and section references match.'}
                  </p>
                </div>

                {/* Safeguard 5: Scope & Applicability */}
                <div className="safeguard-card">
                  <div className="safeguard-top">
                    <span className="safeguard-icon">🌐</span>
                    <span className="safeguard-title">Scope &amp; Applicability</span>
                  </div>
                  <span
                    className={`safeguard-badge ${
                      scopeShifts.length > 0 ? 'alert' : 'safe'
                    }`}
                  >
                    {scopeShifts.length > 0 ? '⚠️ Scope Altered' : '✓ Scope Intact'}
                  </span>
                  <p className="safeguard-detail">
                    {scopeShifts.length > 0
                      ? scopeShifts[0].details
                      : 'Territorial, demographic, and institutional statutory application preserved.'}
                  </p>
                </div>
              </div>
            </div>

            {/* Text Differences: Omissions & Additions */}
            {(omittedSegments.length > 0 || addedSegments.length > 0) && (
              <div className="diff-section">
                <div className="diff-header">
                  <h3 className="subsection-title">Text Alignment &amp; Structural Differences</h3>
                  {textDiffs.length_compression_ratio !== undefined && (
                    <span className="diff-meta">
                      Compression: {(textDiffs.length_compression_ratio * 100).toFixed(0)}% &bull; Overlap: {(textDiffs.lexical_overlap_ratio * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                <div className="diff-content">
                  {omittedSegments.length > 0 && (
                    <div className="diff-group">
                      <span className="diff-group-label omitted">&minus; Omitted in Simplification:</span>
                      <div className="diff-tags">
                        {omittedSegments.slice(0, 10).map((seg, idx) => (
                          <span key={idx} className="diff-tag omitted">
                            {seg}
                          </span>
                        ))}
                        {omittedSegments.length > 10 && (
                          <span className="diff-tag-more">
                            +{omittedSegments.length - 10} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {addedSegments.length > 0 && (
                    <div className="diff-group">
                      <span className="diff-group-label added">&#43; Added in Simplification:</span>
                      <div className="diff-tags">
                        {addedSegments.slice(0, 10).map((seg, idx) => (
                          <span key={idx} className="diff-tag added">
                            {seg}
                          </span>
                        ))}
                        {addedSegments.length > 10 && (
                          <span className="diff-tag-more">
                            +{addedSegments.length - 10} more
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Small Neutral Disclaimer Note near bottom */}
            <div className="disclaimer-note">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span>Automated assessment; legal review may be required.</span>
            </div>
          </section>
        )}
      </main>

      {/* =====================================================================
          6. SAAS FOOTER
          ===================================================================== */}
      <footer className="site-footer">
        <div className="footer-container">
          <div className="footer-brand">
            <span className="footer-brand-name">JUDGEBERT</span>
            <p className="footer-tagline">
              Explainable Multilingual Legal Meaning Preservation Platform for English and Hindi Statutory Text.
            </p>
          </div>
          <div className="footer-links">
            <button
              type="button"
              className="footer-link"
              onClick={() => scrollToSection('home')}
            >
              Home
            </button>
            <button
              type="button"
              className="footer-link"
              onClick={() => scrollToSection('how-it-works')}
            >
              How It Works
            </button>
            <button
              type="button"
              className="footer-link"
              onClick={() => scrollToSection('compare')}
            >
              Compare Texts
            </button>
          </div>
        </div>
        <div className="footer-bottom">
          <p>
            &copy; {new Date().getFullYear()} JUDGEBERT &bull; Automated Legal Meaning Preservation Platform &bull; Automated assessment; legal review may be required.
          </p>
        </div>
      </footer>
    </div>
  );
}
