"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Circle, MapContainer, Marker, TileLayer, useMap, useMapEvents, ZoomControl } from "react-leaflet";
import L, { LatLngLiteral } from "leaflet";
import "leaflet/dist/leaflet.css";

type Props = {
  center: LatLngLiteral;
  radius: number;
  onChange: (value: LatLngLiteral) => void;
  onAddressResolved?: (address: string) => void;
};

// SVG pin icon to avoid broken asset URL issues in Next.js
const customPinIcon = L.divIcon({
  className: "custom-map-pin",
  html: `
    <div style="
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      background: #176b3a;
      color: white;
      border: 2px solid white;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      box-shadow: 0 3px 8px rgba(0,0,0,0.35);
    ">
      <span style="transform: rotate(45deg); font-size: 16px;">🌱</span>
    </div>
  `,
  iconSize: [36, 36],
  iconAnchor: [18, 36],
  popupAnchor: [0, -36],
});

function MapController({ center }: { center: LatLngLiteral }) {
  const map = useMap();
  useEffect(() => {
    // Invalidate map size to ensure full container width and height
    const t = setTimeout(() => {
      map.invalidateSize();
    }, 200);
    return () => clearTimeout(t);
  }, [map]);

  const prevCenterRef = useRef(center);
  useEffect(() => {
    if (
      Math.abs(prevCenterRef.current.lat - center.lat) > 0.0001 ||
      Math.abs(prevCenterRef.current.lng - center.lng) > 0.0001
    ) {
      map.flyTo([center.lat, center.lng], Math.max(map.getZoom(), 11), { duration: 1.2 });
      prevCenterRef.current = center;
    }
  }, [center, map]);

  return null;
}

function LocationEvents({ onChange }: { onChange: (value: LatLngLiteral) => void }) {
  useMapEvents({
    click(event) {
      onChange(event.latlng);
    },
  });
  return null;
}

export default function MapPicker({ center, radius, onChange, onAddressResolved }: Props) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [resolvedAddress, setResolvedAddress] = useState("");

  // Reverse geocode to resolve place name
  const resolveLocationName = useCallback(async (lat: number, lng: number) => {
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=14&addressdetails=1`,
        { headers: { "Accept-Language": "en" } }
      );
      if (res.ok) {
        const data = await res.json();
        const display = data.display_name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        setResolvedAddress(display);
        onAddressResolved?.(display);
      }
    } catch {
      // Fallback
    }
  }, [onAddressResolved]);

  // Handle click / drag
  const handleCoordChange = (newCenter: LatLngLiteral) => {
    onChange(newCenter);
    resolveLocationName(newCenter.lat, newCenter.lng);
  };

  // Search places in India
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true);
    setShowResults(true);
    try {
      const res = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          searchQuery
        )}&countrycodes=in&limit=5`,
        { headers: { "Accept-Language": "en" } }
      );
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      }
    } catch {
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  };

  const handleSelectResult = (item: any) => {
    const lat = parseFloat(item.lat);
    const lng = parseFloat(item.lon);
    if (!isNaN(lat) && !isNaN(lng)) {
      handleCoordChange({ lat, lng });
      setResolvedAddress(item.display_name);
      setShowResults(false);
      setSearchQuery(item.display_name.split(",")[0]);
    }
  };

  // Calculate area
  const areaHectares = (Math.PI * radius * radius) / 10000;
  const areaAcres = areaHectares * 2.47105;
  const areaSqKm = (Math.PI * radius * radius) / 1000000;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, width: "100%" }}>
      {/* Search Bar & Quick Jump */}
      <div style={{ position: "relative", zIndex: 1001 }}>
        <div style={{ display: "flex", gap: 8 }}>
          <div style={{ position: "relative", flex: 1 }}>
            <input
              type="text"
              placeholder="Search Indian village, town, district or state (e.g. Warangal, Vijayawada, Nashik)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleSearch();
                }
              }}
              onFocus={() => searchResults.length > 0 && setShowResults(true)}
              style={{
                width: "100%",
                padding: "10px 14px",
                borderRadius: "8px",
                border: "1px solid #c9ddcc",
                fontSize: "0.88rem",
                background: "#ffffff",
                boxShadow: "0 2px 4px rgba(0,0,0,0.04)",
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  setSearchResults([]);
                  setShowResults(false);
                }}
                style={{
                  position: "absolute",
                  right: 10,
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: "#888",
                  fontSize: "14px",
                }}
              >
                ✕
              </button>
            )}
          </div>
          <button
            type="button"
            onClick={() => handleSearch()}
            disabled={searching}
            style={{
              padding: "10px 18px",
              background: "#176b3a",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontWeight: 600,
              cursor: "pointer",
              fontSize: "0.85rem",
              display: "flex",
              alignItems: "center",
              gap: 6,
              boxShadow: "0 2px 4px rgba(23,107,58,0.25)",
            }}
          >
            {searching ? "Searching..." : "🔍 Search Map"}
          </button>
        </div>

        {/* Dropdown Results */}
        {showResults && searchResults.length > 0 && (
          <div
            style={{
              position: "absolute",
              top: "100%",
              left: 0,
              right: 0,
              marginTop: 4,
              background: "white",
              borderRadius: 8,
              border: "1px solid #c9ddcc",
              boxShadow: "0 8px 18px rgba(0,0,0,0.12)",
              maxHeight: 220,
              overflowY: "auto",
              zIndex: 1002,
            }}
          >
            {searchResults.map((item, idx) => (
              <div
                key={idx}
                onClick={() => handleSelectResult(item)}
                style={{
                  padding: "10px 14px",
                  fontSize: "0.82rem",
                  cursor: "pointer",
                  borderBottom: idx < searchResults.length - 1 ? "1px solid #f0f4f1" : "none",
                  color: "#2d3748",
                  transition: "background 0.15s ease",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#f0fdf4")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "white")}
              >
                📍 <strong>{item.display_name.split(",")[0]}</strong>
                <span style={{ color: "#666", fontSize: "0.75rem", display: "block" }}>
                  {item.display_name}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Interactive Map Container */}
      <div
        style={{
          height: 480,
          width: "100%",
          borderRadius: "12px",
          border: "2px solid #c9ddcc",
          overflow: "hidden",
          position: "relative",
          boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
        }}
      >
        <MapContainer
          center={center}
          zoom={6}
          minZoom={4}
          maxZoom={18}
          scrollWheelZoom={true}
          zoomControl={false}
          style={{ height: "100%", width: "100%" }}
        >
          <ZoomControl position="topright" />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapController center={center} />
          <LocationEvents onChange={handleCoordChange} />
          <Marker
            position={center}
            icon={customPinIcon}
            draggable={true}
            eventHandlers={{
              dragend(event) {
                handleCoordChange(event.target.getLatLng());
              },
            }}
          />
          <Circle
            center={center}
            radius={radius}
            pathOptions={{
              color: "#176b3a",
              weight: 2,
              fillColor: "#3fbb6d",
              fillOpacity: 0.18,
            }}
          />
        </MapContainer>

        {/* Map Legend & Pin Guidance floating inside map */}
        <div
          style={{
            position: "absolute",
            bottom: 12,
            left: 12,
            background: "rgba(255, 255, 255, 0.94)",
            backdropFilter: "blur(4px)",
            padding: "8px 12px",
            borderRadius: "6px",
            boxShadow: "0 2px 6px rgba(0,0,0,0.15)",
            fontSize: "0.76rem",
            color: "#176b3a",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: 6,
            zIndex: 999,
          }}
        >
          <span>📍 Click map or drag pin to select field location</span>
        </div>
      </div>

      {/* Coordinate & Area Summary Bar */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
          padding: "10px 16px",
          background: "#f0fdf4",
          border: "1px solid #bbf7d0",
          borderRadius: "8px",
          fontSize: "0.82rem",
          color: "#166534",
        }}
      >
        <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
          <span>
            Latitude: <strong>{center.lat.toFixed(6)}° N</strong>
          </span>
          <span>
            Longitude: <strong>{center.lng.toFixed(6)}° E</strong>
          </span>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span>
            Buffer Radius: <strong>{(radius / 1000).toFixed(1)} km</strong> ({radius.toLocaleString()} m)
          </span>
          <span>
            Area: <strong>{areaHectares.toFixed(1)} ha</strong> ({areaAcres.toFixed(1)} acres · {areaSqKm.toFixed(2)} km²)
          </span>
        </div>
      </div>
      {resolvedAddress && (
        <div style={{ fontSize: "0.78rem", color: "#4b5563", paddingLeft: 4 }}>
          📌 Selected Location: <em>{resolvedAddress}</em>
        </div>
      )}
    </div>
  );
}
