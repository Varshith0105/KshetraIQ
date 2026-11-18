"use client";

import Link from "next/link";
import { useEffect } from "react";
import { SATELLITE_NDVI_APP_URL } from "../constants";

export default function SatelliteIntelligenceRedirectPage() {
  useEffect(() => {
    // Attempt automatic popup/open in new tab on direct page visit
    const timer = setTimeout(() => {
      window.open(SATELLITE_NDVI_APP_URL, "_blank", "noopener,noreferrer");
    }, 1200);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 50%, #e0f2fe 100%)",
        padding: 24,
        textAlign: "center",
        fontFamily: "system-ui, -apple-system, sans-serif",
      }}
    >
      <div
        style={{
          background: "#ffffff",
          padding: "44px 36px",
          borderRadius: 20,
          border: "1px solid #bbf7d0",
          maxWidth: 620,
          boxShadow: "0 10px 30px rgba(0,0,0,0.08)",
        }}
      >
        <div style={{ fontSize: "52px", marginBottom: 16 }}>🛰️</div>
        <h1 style={{ fontSize: "1.65rem", fontWeight: 800, color: "#14532d", margin: "0 0 12px 0" }}>
          Satellite Intelligence &amp; Multi-Spectral NDVI
        </h1>
        <p style={{ fontSize: "0.95rem", color: "#374151", lineHeight: 1.6, margin: "0 0 24px 0" }}>
          Sentinel-2 cloud-filtered multi-spectral vegetative health (NDVI &amp; EVI) monitoring is deployed as a dedicated cloud application.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
          <a
            href={SATELLITE_NDVI_APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              padding: "14px 28px",
              background: "#15803d",
              color: "#ffffff",
              borderRadius: 10,
              textDecoration: "none",
              fontWeight: 700,
              fontSize: "1rem",
              boxShadow: "0 4px 14px rgba(21,128,61,0.25)",
              transition: "transform 0.15s ease",
            }}
          >
            <span>Launch Satellite NDVI Platform</span>
            <span>↗</span>
          </a>

          <Link
            href="/dashboard"
            style={{
              display: "inline-block",
              marginTop: 10,
              padding: "8px 16px",
              color: "#4b5563",
              fontSize: "0.88rem",
              textDecoration: "none",
              fontWeight: 500,
            }}
          >
            ← Return to KshetraIQ Dashboard
          </Link>
        </div>

        <div
          style={{
            marginTop: 32,
            padding: "12px 16px",
            background: "#f0fdf4",
            borderRadius: 8,
            border: "1px solid #dcfce7",
            fontSize: "0.82rem",
            color: "#166534",
          }}
        >
          Target Application: <code>{SATELLITE_NDVI_APP_URL}</code>
        </div>
      </div>
    </div>
  );
}
