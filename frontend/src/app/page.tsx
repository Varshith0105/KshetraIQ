"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "./context/AuthContext";
import {
  LeafIcon,
  FlaskIcon,
  CloudSunIcon,
  ShieldCheckIcon,
  FileTextIcon,
  CheckCircleIcon,
  ArrowRightIcon,
  SparklesIcon,
  BarChartIcon,
  DropletIcon,
  TrendingUpIcon,
  BugIcon,
  BotIcon,
  MenuIcon,
  XIcon,
  UserIcon,
} from "./components/Icons";

type Lang = "en" | "te";

export default function LandingPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [lang, setLang] = useState<Lang>("en");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="landing-page-root">
      {/* ───────────────── 1. NAVBAR ───────────────── */}
      <header className="landing-header">
        <div className="landing-header-container">
          {/* Brand Logo & Tagline */}
          <Link href="/" className="landing-logo-group">
            <div className="landing-logo-icon">
              <LeafIcon size={22} />
            </div>
            <div>
              <div className="landing-brand-title">
                Kshetra<span>IQ</span>
              </div>
              <div className="landing-brand-subtitle">
                {lang === "te" ? "వ్యవసాయ AI మేధస్సు" : "AI Agricultural Intelligence"}
              </div>
            </div>
          </Link>

          {/* Desktop Navigation Links */}
          <nav className="landing-desktop-nav">
            <a href="#features" className="landing-nav-link">
              {lang === "te" ? "విభాగాలు" : "Features"}
            </a>
            <a href="#how-it-works" className="landing-nav-link">
              {lang === "te" ? "పనిచేసే విధానం" : "How It Works"}
            </a>
            <a href="#technology" className="landing-nav-link">
              {lang === "te" ? "సాంకేతికత" : "Our Technology"}
            </a>
            <a href="#contact" className="landing-nav-link">
              {lang === "te" ? "సంప్రదించండి" : "Contact"}
            </a>
          </nav>

          {/* Right Header Actions */}
          <div className="landing-nav-actions">
            {/* Language Switcher */}
            <div
              style={{
                display: "inline-flex",
                background: "#eaf3eb",
                padding: 3,
                borderRadius: 8,
                border: "1px solid #d4e5d6",
              }}
            >
              <button
                type="button"
                onClick={() => setLang("en")}
                style={{
                  border: "none",
                  background: lang === "en" ? "#fff" : "transparent",
                  color: lang === "en" ? "#104D2B" : "#557a5b",
                  fontWeight: 600,
                  fontSize: "0.78rem",
                  padding: "4px 9px",
                  borderRadius: 6,
                  cursor: "pointer",
                  boxShadow: lang === "en" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
                }}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLang("te")}
                style={{
                  border: "none",
                  background: lang === "te" ? "#fff" : "transparent",
                  color: lang === "te" ? "#104D2B" : "#557a5b",
                  fontWeight: 600,
                  fontSize: "0.78rem",
                  padding: "4px 9px",
                  borderRadius: 6,
                  cursor: "pointer",
                  boxShadow: lang === "te" ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
                }}
              >
                తెలుగు
              </button>
            </div>

            {/* Auth Buttons */}
            {user ? (
              <button
                type="button"
                onClick={() => router.push("/dashboard")}
                className="btn-primary-pill"
                style={{ padding: "10px 18px", fontSize: "0.88rem" }}
              >
                <UserIcon size={16} />
                <span>{lang === "te" ? "డాష్‌బోర్డ్" : "Dashboard"}</span>
                <ArrowRightIcon size={14} />
              </button>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Link
                  href="/login"
                  style={{
                    padding: "9px 16px",
                    borderRadius: 999,
                    fontSize: "0.88rem",
                    fontWeight: 600,
                    color: "#104D2B",
                    textDecoration: "none",
                    border: "1px solid #c9decb",
                    background: "#ffffff",
                    transition: "all 0.2s ease",
                  }}
                >
                  {lang === "te" ? "లాగిన్" : "Sign In"}
                </Link>
                <Link
                  href="/signup"
                  className="btn-primary-pill"
                  style={{ padding: "10px 20px", fontSize: "0.88rem" }}
                >
                  {lang === "te" ? "ఖాతా తెరవండి" : "Get Started"}
                </Link>
              </div>
            )}

            {/* Mobile Hamburger Toggle */}
            <button
              type="button"
              className="landing-mobile-toggle"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <XIcon size={24} /> : <MenuIcon size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div
            style={{
              padding: "16px 24px",
              background: "#ffffff",
              borderTop: "1px solid #e2eae3",
              display: "flex",
              flexDirection: "column",
              gap: 14,
            }}
          >
            <a
              href="#features"
              onClick={() => setMobileMenuOpen(false)}
              className="landing-nav-link"
              style={{ fontSize: "1rem", padding: "6px 0" }}
            >
              {lang === "te" ? "విభాగాలు" : "Features"}
            </a>
            <a
              href="#how-it-works"
              onClick={() => setMobileMenuOpen(false)}
              className="landing-nav-link"
              style={{ fontSize: "1rem", padding: "6px 0" }}
            >
              {lang === "te" ? "పనిచేసే విధానం" : "How It Works"}
            </a>
            <a
              href="#technology"
              onClick={() => setMobileMenuOpen(false)}
              className="landing-nav-link"
              style={{ fontSize: "1rem", padding: "6px 0" }}
            >
              {lang === "te" ? "సాంకేతికత" : "Our Technology"}
            </a>
            <a
              href="#contact"
              onClick={() => setMobileMenuOpen(false)}
              className="landing-nav-link"
              style={{ fontSize: "1rem", padding: "6px 0" }}
            >
              {lang === "te" ? "సంప్రదించండి" : "Contact"}
            </a>
            <div style={{ paddingTop: 8, display: "flex", gap: 10 }}>
              {user ? (
                <Link
                  href="/dashboard"
                  className="btn-primary-pill"
                  style={{ width: "100%", justifyContent: "center" }}
                >
                  {lang === "te" ? "డాష్‌బోర్డ్ తెరవండి" : "Open Dashboard"}
                </Link>
              ) : (
                <>
                  <Link
                    href="/login"
                    style={{
                      flex: 1,
                      textAlign: "center",
                      padding: "10px",
                      borderRadius: 8,
                      border: "1px solid #c9decb",
                      textDecoration: "none",
                      color: "#104D2B",
                      fontWeight: 600,
                    }}
                  >
                    {lang === "te" ? "లాగిన్" : "Sign In"}
                  </Link>
                  <Link
                    href="/signup"
                    className="btn-primary-pill"
                    style={{ flex: 1, justifyContent: "center" }}
                  >
                    {lang === "te" ? "ఖాతా తెరవండి" : "Get Started"}
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* ───────────────── 2. HERO SECTION ───────────────── */}
      <section className="landing-hero">
        <div className="landing-hero-grid">
          <div>
            <div className="hero-pill-badge">
              <SparklesIcon size={14} />
              <span>
                {lang === "te"
                  ? "ICAR/ANGRAU ప్రమాణాలతో కూడిన AI అడ్వైజరీ"
                  : "Verified AI Agronomy & ICAR/ANGRAU Aligned"}
              </span>
            </div>

            <h1 className="hero-main-heading">
              {lang === "te" ? (
                <>
                  తెలివిగా సాగు చేయండి. <br />
                  <span className="highlight-green">అధిక దిగుబడి సాధించండి.</span>
                </>
              ) : (
                <>
                  Smarter Decisions for Healthier Fields <br />
                  <span className="highlight-green">and Brighter Futures.</span>
                </>
              )}
            </h1>

            <p className="hero-subheading">
              {lang === "te"
                ? "నేల పరీక్ష విశ్లేషణ, రీఇన్‌ఫోర్స్‌మెంట్ లెర్నింగ్ నీటి యాజమాన్యం, వాతావరణ ముందస్తు అంచనాలు మరియు ఏపీఎంసీ మార్కెట్ ధరల విశ్లేషణతో ప్రతి నిర్ణయాన్ని పక్కాగా తీసుకోండి."
                : "Make informed agricultural decisions with precision AI crop recommendations, soil health analytics, reinforcement learning irrigation planning, weather risk intelligence, and APMC mandi market forecasts."}
            </p>

            <div className="hero-cta-row">
              <Link href="/signup" className="btn-primary-pill">
                <span>{lang === "te" ? "ఉచితంగా ప్రారంభించండి" : "Get Started Free"}</span>
                <ArrowRightIcon size={16} />
              </Link>
              <a href="#features" className="btn-secondary-pill">
                <span>{lang === "te" ? "ప్రత్యేకతలు చూడండి" : "Explore Features"}</span>
              </a>
            </div>
          </div>

          {/* Free Pexels source: Rubenstein Rebello, photo 31983759 (Pexels License). */}
          <div className="hero-visual-card">
            <div className="hero-image-frame" role="img" aria-label="Indian farmer standing in a verdant field">
              <img
                src="https://images.pexels.com/photos/31983759/pexels-photo-31983759.jpeg?cs=srgb&dl=pexels-rubenstein111rebello-31983759.jpg&fm=jpg"
                alt="Indian farmer standing in a lush green field"
                loading="eager"
              />
              <div className="hero-image-overlay" />
            </div>

            {/* Floating Telemetry Badge 1: PPO RL Irrigation */}
            <div className="floating-telemetry-badge floating-badge-top-right">
              <div
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: 10,
                  background: "#eaf3fc",
                  color: "#1565a8",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <DropletIcon size={20} />
              </div>
              <div>
                <div style={{ fontSize: "0.74rem", color: "#6b756d", fontWeight: 600 }}>
                  {lang === "te" ? "PPO నీటి యాజమాన్యం" : "PPO RL Irrigation"}
                </div>
                <div style={{ fontSize: "0.95rem", fontWeight: 800, color: "#104D2B" }}>
                  18 mm / Acre (Canal)
                </div>
              </div>
            </div>

            {/* Floating Telemetry Badge 2: Soil Health Index */}
            <div className="floating-telemetry-badge floating-badge-bottom-left">
              <div
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: 10,
                  background: "#edf8f0",
                  color: "#104D2B",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <FlaskIcon size={20} />
              </div>
              <div>
                <div style={{ fontSize: "0.74rem", color: "#6b756d", fontWeight: 600 }}>
                  {lang === "te" ? "నేల ఆరోగ్యం (గుంటూరు)" : "Soil Health (Clay Loam)"}
                </div>
                <div style={{ fontSize: "0.95rem", fontWeight: 800, color: "#104D2B" }}>
                  pH 7.2 • NPK 140:35:190
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────── 3. TRUST & PLATFORM CAPABILITIES STRIP ───────────────── */}
      <section className="trust-strip">
        <div className="trust-strip-container">
          <div className="trust-stat-box">
            <div className="trust-stat-icon">
              <SparklesIcon size={24} />
            </div>
            <div>
              <div className="trust-stat-val">12 Modules</div>
              <div className="trust-stat-lbl">
                {lang === "te" ? "పూర్తి వ్యవసాయ AI సూచనలు" : "Complete Agri-Intelligence Modules"}
              </div>
            </div>
          </div>

          <div className="trust-stat-box">
            <div className="trust-stat-icon">
              <DropletIcon size={24} />
            </div>
            <div>
              <div className="trust-stat-val">PPO + ICAR</div>
              <div className="trust-stat-lbl">
                {lang === "te" ? "సురక్షిత రీఇన్‌ఫోర్స్‌మెంట్ లెర్నింగ్" : "Reinforcement Learning & Safe Fallback"}
              </div>
            </div>
          </div>

          <div className="trust-stat-box">
            <div className="trust-stat-icon">
              <TrendingUpIcon size={24} />
            </div>
            <div>
              <div className="trust-stat-val">8 APMC Mandis</div>
              <div className="trust-stat-lbl">
                {lang === "te" ? "ధరల ముందస్తు అంచనా మోడల్స్" : "Multi-Crop Price Projections"}
              </div>
            </div>
          </div>

          <div className="trust-stat-box">
            <div className="trust-stat-icon">
              <BotIcon size={24} />
            </div>
            <div>
              <div className="trust-stat-val">EN + తెలుగు</div>
              <div className="trust-stat-lbl">
                {lang === "te" ? "రైతు మిత్ర AI సంభాషణ" : "Bilingual Rythu AI Assistant"}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────── 4. FEATURES SECTION ───────────────── */}
      <section id="features" className="landing-section">
        <div className="section-header-center">
          <span className="section-tag">{lang === "te" ? "సామర్థ్యాలు" : "Platform Capabilities"}</span>
          <h2 className="section-heading">
            {lang === "te"
              ? "ప్రతి రైతుకు ఆధునిక విజ్ఞాన సాధనాలు"
              : "Comprehensive Intelligence for Modern Agriculture"}
          </h2>
          <p className="section-desc">
            {lang === "te"
              ? "క్షేత్ర పరిశీలనలు, ఉపగ్రహ వాతావరణం మరియు అధునాతన మెషిన్ లెర్నింగ్ కలయికతో రూపొందించబడిన సమగ్ర వ్యవస్థ."
              : "Engineered from certified soil lab tests, real-time agro-meteorology, and validated machine learning models to maximize seasonal crop viability."}
          </p>
        </div>

        <div className="features-grid">
          {/* 1. Soil Health Intelligence */}
          <div className="feature-modern-card">
            <div className="feature-icon-badge">
              <FlaskIcon size={26} />
            </div>
            <h3 className="feature-card-title">
              {lang === "te" ? "నేల ఆరోగ్య విశ్లేషణ" : "Soil Health Intelligence"}
            </h3>
            <p className="feature-card-desc">
              {lang === "te"
                ? "NPK నిష్పత్తి, సేంద్రీయ కర్బనం మరియు pH సమతుల్యతను లెక్కించి, నిర్దిష్ట పంటకు అవసరమైన ఎరువుల మోతాదును సూచిస్తుంది."
                : "Evaluates Nitrogen, Phosphorus, Potassium, Organic Carbon, and pH to calculate precise deficiency remedies and optimal fertilizer schedules."}
            </p>
            <span className="feature-card-badge">Lab-Verified Diagnostics</span>
          </div>

          {/* 2. AI Crop Recommendations */}
          <div className="feature-modern-card">
            <div className="feature-icon-badge">
              <LeafIcon size={26} />
            </div>
            <h3 className="feature-card-title">
              {lang === "te" ? "పంట సిఫార్సులు" : "AI Crop Recommendations"}
            </h3>
            <p className="feature-card-desc">
              {lang === "te"
                ? "నేల రకం, నీటి వసతి, ఖరీఫ్/రబీ కాలాలు మరియు బడ్జెట్ ఆధారంగా అత్యధిక లాభదాయక పంటలను ర్యాంక్ చేస్తుంది."
                : "Ranks multi-crop options suited to your specific soil texture, seasonal agro-climatic window, and irrigation constraints."}
            </p>
            <span className="feature-card-badge">Kharif / Rabi / Zaid</span>
          </div>

          {/* 3. Smart RL Irrigation */}
          <div className="feature-modern-card">
            <div className="feature-icon-badge">
              <DropletIcon size={26} />
            </div>
            <h3 className="feature-card-title">
              {lang === "te" ? "స్మార్ట్ నీటి యాజమాన్యం" : "Smart RL Irrigation"}
            </h3>
            <p className="feature-card-desc">
              {lang === "te"
                ? "PPO రీఇన్‌ఫోర్స్‌మెంట్ లెర్నింగ్ మోడల్ మరియు ICAR ANGRAU నియమాలతో ఎకరానికి కావలసిన నీటి పరిమాణాన్ని ఖచ్చితంగా నిర్ణయిస్తుంది."
                : "Continuous PPO Reinforcement Learning policy and ICAR/ANGRAU fallback calculate exact water depth (mm) and litres per acre."}
            </p>
            <span className="feature-card-badge">PPO Policy + ICAR Fallback</span>
          </div>

          {/* 4. Weather Intelligence */}
          <div className="feature-modern-card">
            <div className="feature-icon-badge">
              <CloudSunIcon size={26} />
            </div>
            <h3 className="feature-card-title">
              {lang === "te" ? "వాతావరణ ముందస్తు హెచ్చరికలు" : "Weather Intelligence"}
            </h3>
            <p className="feature-card-desc">
              {lang === "te"
                ? "గ్రామ మరియు మండల స్థాయి వర్షపాతం, ఉష్ణోగ్రత మరియు గాలి తేమను పరిశీలించి ప్రతికూల వాతావరణ హెచ్చరికలు ఇస్తుంది."
                : "High-resolution 7-day meteorological forecasts track heat stress, humidity spikes, and precipitation to mitigate harvest loss."}
            </p>
            <span className="feature-card-badge">Real-Time OpenWeather</span>
          </div>

          {/* 5. Market Price Forecast */}
          <div className="feature-modern-card">
            <div className="feature-icon-badge">
              <TrendingUpIcon size={26} />
            </div>
            <h3 className="feature-card-title">
              {lang === "te" ? "మార్కెట్ ధరల విశ్లేషణ" : "Market Price Forecast"}
            </h3>
            <p className="feature-card-desc">
              {lang === "te"
                ? "రాష్ట్రంలోని ప్రధాన మార్కెట్లలో పంట రాక మరియు చారిత్రక ధరల సరళిని విశ్లేషించి సరైన విక్రయ సమయాన్ని అంచనా వేస్తుంది."
                : "Ensemble price projection models analyze seasonal market arrivals across APMC mandis to recommend optimal selling timeframes."}
            </p>
            <span className="feature-card-badge">8 Mandi Crops Supported</span>
          </div>

          {/* 6. Plant Disease Screening */}
          <div className="feature-modern-card">
            <div className="feature-icon-badge">
              <BugIcon size={26} />
            </div>
            <h3 className="feature-card-title">
              {lang === "te" ? "తెగుళ్ల గుర్తింపు & చికిత్స" : "Plant Disease Screening"}
            </h3>
            <p className="feature-card-desc">
              {lang === "te"
                ? "ఆకుల ఫోటో ద్వారా పంట తెగుళ్లను గుర్తించి, సేంద్రీయ మరియు రసాయన నివారణ చర్యలను తక్షణమే అందిస్తుంది."
                : "ResNet-50 computer vision architecture classifies foliar lesions, bacterial blights, and provides immediate agronomic countermeasures."}
            </p>
            <span className="feature-card-badge">ResNet-50 Vision</span>
          </div>

          {/* 7. Comprehensive PDF Reports */}
          <div className="feature-modern-card">
            <div className="feature-icon-badge">
              <FileTextIcon size={26} />
            </div>
            <h3 className="feature-card-title">
              {lang === "te" ? "సమగ్ర రైతు నివేదిక" : "Comprehensive Advisory Reports"}
            </h3>
            <p className="feature-card-desc">
              {lang === "te"
                ? "మీ క్షేత్రానికి సంబంధించిన సమగ్ర సూచనలను డాక్యుమెంట్‌గా డౌన్‌లోడ్ చేసుకుని స్థానిక వ్యవసాయ అధికారులతో సంప్రదించవచ్చు."
                : "Generates formatted PDF advisory records detailing soil chemistry, crop schedules, and water budgets for field extension officers."}
            </p>
            <span className="feature-card-badge">Printable PDF Advisory</span>
          </div>

          {/* 8. Bilingual Rythu AI Chatbot */}
          <div className="feature-modern-card">
            <div className="feature-icon-badge">
              <BotIcon size={26} />
            </div>
            <h3 className="feature-card-title">
              {lang === "te" ? "రైతు AI మిత్రుడు" : "Rythu AI Chatbot"}
            </h3>
            <p className="feature-card-desc">
              {lang === "te"
                ? "రైతుల ప్రశ్నలకు తెలుగు మరియు ఇంగ్లీష్ భాషలలో వ్యవసాయ రంగ నిపుణుల మార్గదర్శకాలను తక్షణమే అందిస్తుంది."
                : "Conversational advisory assistant fluent in Telugu and English, answering questions about pest control, seed varieties, and soil amendments."}
            </p>
            <span className="feature-card-badge">Telugu & English Audio</span>
          </div>
        </div>
      </section>

      {/* ───────────────── 5. HOW IT WORKS ───────────────── */}
      <section id="how-it-works" className="how-it-works-bg">
        <div className="landing-section">
          <div className="section-header-center">
            <span className="section-tag">{lang === "te" ? "ప్రక్రియ" : "Simple 3-Step Process"}</span>
            <h2 className="section-heading">
              {lang === "te" ? "సులభమైన మూడు దశల ప్రయాణం" : "From Soil Sample to Field Action"}
            </h2>
            <p className="section-desc">
              {lang === "te"
                ? "క్లిష్టమైన గణాంకాలను సరళమైన ఆచరణాత్మక కార్యాచరణగా మార్చే విధానం."
                : "KshetraIQ bridges certified agronomic laboratory science with actionable daily farm workflows."}
            </p>
          </div>

          <div className="steps-flow-grid">
            {/* Step 1 */}
            <div className="step-flow-card">
              <div className="step-num-pill">1</div>
              <h3 className="step-title">
                {lang === "te" ? "క్షేత్ర వివరాలు నమోదు చేయండి" : "1. Enter Farm Parameters"}
              </h3>
              <p className="step-desc">
                {lang === "te"
                  ? "మీ పొలం విస్తీర్ణం, జిల్లా, గ్రామం, నీటి వనరు మరియు నేల పరీక్ష ఫలితాలను సులభమైన ఫారమ్ ద్వారా నమోదు చేయండి."
                  : "Input your land acreage, district, water source, and laboratory soil test metrics (NPK, pH, organic carbon)."}
              </p>
            </div>

            {/* Step 2 */}
            <div className="step-flow-card">
              <div className="step-num-pill">2</div>
              <h3 className="step-title">
                {lang === "te" ? "AI విశ్లేషణను పరిశీలించండి" : "2. Multi-Model Agronomic Synthesis"}
              </h3>
              <p className="step-desc">
                {lang === "te"
                  ? "మా మెషిన్ లెర్నింగ్ మోడల్స్ మరియు ICAR సూత్రాలు పంట అనుకూలత, నీటి అవసరం మరియు వాతావరణ నష్టాలను తక్షణమే లెక్కిస్తాయి."
                  : "KshetraIQ evaluates crop suitability, PPO reinforcement learning irrigation depths, and real-time weather risk projections."}
              </p>
            </div>

            {/* Step 3 */}
            <div className="step-flow-card">
              <div className="step-num-pill">3</div>
              <h3 className="step-title">
                {lang === "te" ? "ఆచరణాత్మక నిర్ణయాలు తీసుకోండి" : "3. Implement Field Actions"}
              </h3>
              <p className="step-desc">
                {lang === "te"
                  ? "ఖచ్చితమైన నీటి విడుదల, ఎరువుల సమతుల్యత మరియు అధిక ధర వచ్చే సమయానికి అనుగుణంగా పంట విక్రయాన్ని నిర్వహించండి."
                  : "Apply exact litres of irrigation, prevent disease outbreaks, consult the Rythu AI assistant, and export your official PDF report."}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────── 6. TECHNOLOGY & DATA INTEGRITY ───────────────── */}
      <section id="technology" className="landing-section">
        <div className="section-header-center">
          <span className="section-tag">{lang === "te" ? "పారదర్శకత" : "Model Architecture"}</span>
          <h2 className="section-heading">
            {lang === "te" ? "నిరూపితమైన ఆర్కిటెక్చర్ & భద్రత" : "Engineered on Verified Models"}
          </h2>
          <p className="section-desc">
            {lang === "te"
              ? "అవాస్తవిక గణాంకాలు లేదా కల్పిత సమాచారం లేకుండా నిజమైన శాస్త్రీయ మోడల్స్ ఆధారంగా నిర్మించబడింది."
              : "KshetraIQ maintains strict model contracts, reproducible feature orders, and failsafe agronomic fallbacks."}
          </p>
        </div>

        <div className="tech-models-grid">
          <div className="tech-spec-card">
            <div className="tech-model-type">Reinforcement Learning Policy</div>
            <h3 className="tech-model-name">Proximal Policy Optimization (PPO)</h3>
            <p className="tech-model-desc">
              Actor-Critic policy network trained on dynamic ETc, soil moisture gradients, and precipitation to decide irrigation application depth (0, 6, 12, 18 mm).
            </p>
            <div className="tech-contract-status">
              <CheckCircleIcon size={14} />
              <span>PPO Actor-Critic Verified</span>
            </div>
          </div>

          <div className="tech-spec-card">
            <div className="tech-model-type">Deterministic Safety Net</div>
            <h3 className="tech-model-name">ICAR / ANGRAU Agronomic Engine</h3>
            <p className="tech-model-desc">
              Whenever inputs exceed trained RL bounds or crops are outside Paddy/Groundnut, the system automatically uses verified ICAR/ANGRAU crop-stage factor formulas.
            </p>
            <div className="tech-contract-status">
              <CheckCircleIcon size={14} />
              <span>Deterministic ANGRAU Contract</span>
            </div>
          </div>

          <div className="tech-spec-card">
            <div className="tech-model-type">Deep Computer Vision</div>
            <h3 className="tech-model-name">ResNet-50 Disease Classifier</h3>
            <p className="tech-model-desc">
              Trained deep convolutional network with transfer learning to identify fungal and bacterial blights from leaf surface photography with remedial guidance.
            </p>
            <div className="tech-contract-status">
              <CheckCircleIcon size={14} />
              <span>ResNet-50 Vision Architecture</span>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────── 7. FINAL CALL TO ACTION ───────────────── */}
      <div className="cta-banner-wrapper">
        <div className="cta-banner-card">
          <h2 className="cta-banner-title">
            {lang === "te"
              ? "మీ వ్యవసాయాన్ని డేటాతో బలోపేతం చేయండి"
              : "Ready to Make Smarter Farm Decisions?"}
          </h2>
          <p className="cta-banner-sub">
            {lang === "te"
              ? "నేల పరీక్షతో ప్రారంభించండి, నీటి వృధాను తగ్గించండి మరియు సరైన సమయంలో పంటను అమ్మి అధిక ఆదాయాన్ని పొందండి."
              : "Create your farmer account today to generate custom agronomic assessments, smart irrigation schedules, and APMC market price insights."}
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 14 }}>
            <Link
              href="/signup"
              style={{
                background: "#ffffff",
                color: "#104D2B",
                fontWeight: 700,
                padding: "16px 36px",
                borderRadius: 999,
                textDecoration: "none",
                fontSize: "1.05rem",
                boxShadow: "0 10px 24px rgba(0, 0, 0, 0.2)",
                transition: "transform 0.2s ease",
              }}
            >
              {lang === "te" ? "ఉచిత ఖాతా తెరవండి" : "Create Free Account"}
            </Link>
          </div>
        </div>
      </div>

      {/* ───────────────── 8. FOOTER ───────────────── */}
      <footer id="contact" className="landing-footer">
        <div className="footer-top-grid">
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <div
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: 10,
                  background: "#1d8748",
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <LeafIcon size={18} />
              </div>
              <span style={{ fontSize: "1.3rem", fontWeight: 800, color: "#ffffff" }}>
                Kshetra<span style={{ color: "#34c471" }}>IQ</span>
              </span>
            </div>
            <p style={{ fontSize: "0.86rem", lineHeight: 1.6, color: "#95ad9b", maxWidth: 320 }}>
              AI-Powered Agricultural Intelligence Platform designed for Indian farmers. Providing verified agronomic analytics, precision irrigation, and mandi price projections.
            </p>
          </div>

          <div>
            <h4 className="footer-col-title">Platform</h4>
            <ul className="footer-links-list">
              <li><a href="#features">Soil Health Intelligence</a></li>
              <li><a href="#features">AI Crop Recommendations</a></li>
              <li><a href="#features">PPO RL Irrigation</a></li>
              <li><a href="#features">Mandi Price Forecast</a></li>
            </ul>
          </div>

          <div>
            <h4 className="footer-col-title">Technology</h4>
            <ul className="footer-links-list">
              <li><a href="#technology">PPO Actor-Critic Policy</a></li>
              <li><a href="#technology">ICAR ANGRAU Safety Net</a></li>
              <li><a href="#technology">ResNet-50 Disease Vision</a></li>
              <li><a href="#technology">OpenWeather Integration</a></li>
            </ul>
          </div>

          <div>
            <h4 className="footer-col-title">Access</h4>
            <ul className="footer-links-list">
              <li><Link href="/login">Farmer Sign In</Link></li>
              <li><Link href="/signup">Create New Account</Link></li>
              <li><Link href="/dashboard">Direct Dashboard</Link></li>
            </ul>
          </div>
        </div>

        <div className="footer-disclaimer-box">
          <p style={{ margin: 0 }}>
            <strong>Agricultural Advisory Disclaimer:</strong> KshetraIQ recommendations are algorithmic advisory outputs generated from machine learning models and ICAR/ANGRAU agricultural formulas. They are intended to assist farm decision-making in conjunction with local agricultural extension officers (Krishi Vigyan Kendras - KVKs).
          </p>
          <p style={{ margin: "10px 0 0", color: "#546e5b" }}>
            © {new Date().getFullYear()} KshetraIQ Platform. All rights reserved. Built with Next.js, FastAPI, and PyTorch.
          </p>
        </div>
      </footer>
    </div>
  );
}
