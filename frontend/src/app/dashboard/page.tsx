"use client";

import { FormEvent, useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  LeafIcon,
  FlaskIcon,
  CloudSunIcon,
  MapPinIcon,
  ShieldCheckIcon,
  FileTextIcon,
  CheckCircleIcon,
  AlertCircleIcon,
  InfoIcon,
  ArrowRightIcon,
  SparklesIcon,
  RefreshIcon,
  BarChartIcon,
  SettingsIcon,
  HelpIcon,
  DatabaseIcon,
  MenuIcon,
  UserIcon,
  DropletIcon,
  TrendingUpIcon,
  BugIcon,
  BotIcon,
  XIcon,
  MinusIcon,
  TrashIcon,
  UploadIcon,
  ImageIcon,
  SendIcon,
  MicIcon,
  VolumeIcon,
  VolumeXIcon,
} from "../components/Icons";
import { useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import { useScreenContext } from "../context/ScreenContext";
import { INDIA_LOCATIONS, SUPPORTED_STATES } from "./indiaLocations";
import { SATELLITE_NDVI_APP_URL } from "../constants";

/* ── helpers ─────────────────────────────────────────────── */
function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined" && window.location) {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://localhost:8000";
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function getGreetingTe(): string {
  const h = new Date().getHours();
  if (h < 12) return "శుభోదయం";
  if (h < 17) return "శుభ మధ్యాహ్నం";
  return "శుభ సాయంత్రం";
}

/* ── type definitions ──────────────────────────────────────── */
type Lang = "en" | "te";
type FarmProfile = {
  farm_name: string;
  district: string;
  state: string;
  acreage: number;
  season: string;
  irrigation_method: string;
  water_availability: string;
  updated_at?: string;
};
type View =
  | "dashboard"
  | "profile"
  | "assessment"
  | "recommendations"
  | "results"
  | "weather"
  | "soil"
  | "irrigation"
  | "market"
  | "disease"
  | "reports"
  | "registry"
  | "settings";

type CropCandidate = { crop: string; crop_te: string; confidence: number };
type CropPrediction = {
  recommended_crop: string;
  recommended_crop_te: string;
  confidence: number;
  top_candidates: CropCandidate[];
  features_used: Record<string, number>;
  model_id: string;
  algorithm: string;
};
type ModelResult = {
  model_id: string;
  status: string;
  message: string;
  missing_inputs: string[];
  prediction?: CropPrediction | null;
  contract_note?: string;
};
type Advisor = {
  mode: string;
  provider_note: string;
  summary: string;
  summary_te: string;
  soil_health_assessment: {
    ph_status: string;
    ph_note: string;
    ph_note_te: string;
    npk_observations: string[];
    npk_observations_te: string[];
    score?: number | null;
    category?: string;
    is_provisional?: boolean;
    deficiencies?: string[];
    excesses?: string[];
    methodology?: string;
  };
  crop_guidance: {
    crop: string;
    crop_te: string;
    best_practices: string;
    best_practices_te: string;
  };
  water_and_irrigation: {
    irrigation_type: string;
    water_availability: string;
    acreage: number;
    recommendation: string;
    recommendation_te: string;
  };
  seasonal_risk_management: string[];
  seasonal_risk_management_te: string[];
  disclaimer: string;
};
type ReportPreview = {
  assessment_id: string;
  farm_name: string;
  location: string;
  acreage: number;
  season: string;
  soil: Record<string, number | null>;
  weather: Record<string, number | null>;
  recommended_crop?: string;
  confidence?: number;
  confirmation_prompt: string;
  confirmation_prompt_te: string;
  disclaimer: string;
};
type Assessment = {
  assessment_id: string;
  created_at: string;
  weather_source: string;
  storage: string;
  results: ModelResult[];
  advisor?: Advisor | null;
  assumptions: string[];
  limitations: string[];
  input?: any;
};
type ModelCatalogEntry = {
  model_id: string;
  artifact: string;
  contract_status: string;
  note: string;
  smoke_test_passed?: boolean;
  limitations?: string | null;
  // Extended fields from dual-status registry
  readiness_status?: string;
  prediction_status?: string;
  model_type?: string;
  active_artifact?: string;
  missing_input_explanation?: string;
  last_verified_at?: string;
  runtime_verification_result?: string;
  message?: string;
  missing_inputs?: string[];
};

type UploadedFileItem = {
  file_id: string;
  original_filename: string;
  safe_filename: string;
  file_type: string;
  size_bytes: number;
  category: string;
  storage: string;
  message: string;
};

type ChatMessage = {
  sender: "user" | "bot";
  text: string;
  mode?: string;
  disclaimer?: string;
  contextUsed?: boolean;
};


/* ── translations helper ───────────────────────────────────── */

// Model purposes for the registry card grid (farmer-facing descriptions)
const MODEL_PURPOSES: Record<string, string> = {
  "crop-recommendation-v1": "Recommends optimal crops using soil NPK, pH, and agro-climatic data.",
  "crop-yield-v1": "Estimates harvest yield in tonnes/hectare for a given area.",
  "climate-scenario-v1": "Simulates yield impact under 10% and 25% rainfall stress scenarios.",
  "sustainability-v1": "Scores farm eco-efficiency from chemical inputs and yield outputs.",
  "weather-risk-v1": "Classifies meteorological hazard tier (Low / Moderate / High / Extreme).",
  "market-price-v2": "Forecasts APMC mandi modal prices using persistence and LightGBM hybrid.",
  "irrigation-rl-v1": "Schedules water volume using PPO reinforcement learning + ICAR bounds.",
  "plant-disease-v1": "Diagnoses foliar diseases from ResNet50 leaf image classification.",
};

function useTranslations(language: Lang) {
  const te = (enText: string, teText: string) =>
    language === "te" ? teText : enText;

  return {
    // Nav (12 items)
    navDashboard: te("Dashboard", "డ్యాష్‌బోర్డ్"),
    navProfile: te("Farm Profile", "రైతు ప్రొఫైల్"),
    navAssessment: te("Farm Assessment", "పొలం అంచనా"),
    navCropRec: te("Crop Recommendations", "పంట సిఫార్సులు"),
    navWeather: te("Weather", "వాతావరణం"),
    navSoil: te("Soil Health", "నేల ఆరోగ్యం"),
    navIrrigation: te("Irrigation & Water", "నీటి పారుదల"),
    navMarket: te("Market Insights", "మార్కెట్ సమాచారం"),
    navDisease: te("Plant Disease", "మొక్కల తెగుళ్లు"),
    navReports: te("Reports", "నివేదికలు"),
    navModelRegistry: te("Model Registry", "మోడల్ రిజిస్ట్రీ"),
    navSettings: te("Settings", "సెట్టింగ్స్"),
    navHelp: te("Help", "సహాయం"),
    navDataSources: te("Data Sources", "డేటా వనరులు"),

    // Dashboard
    greeting: te(`${getGreeting()}, Farmer`, `${getGreetingTe()}, రైతు`),
    greetingSub: te(
      "Here's your farm intelligence overview.",
      "మీ పొలం సమాచారం ఇక్కడ ఉంది."
    ),

    // KPI Summary Cards
    kpiLandArea: te("Registered Land Area", "నమోదైన విస్తీర్ణం"),
    kpiLatestAssessment: te("Latest Assessment", "తాజా అంచనా"),
    kpiWeather: te("Current Weather", "ప్రస్తుత వాతావరణం"),
    kpiWeatherSub: te("Open-Meteo live feed", "ఓపెన్-మెటియో లైవ్"),
    kpiCropStatus: te("Recommended Crop", "సిఫార్సు పంట"),
    kpiPersistence: te("Data Persistence", "డేటా నిల్వ"),
    kpiPersistenceSub: te("Supabase not configured", "సుపాబేస్ అమర్చబడలేదు"),

    // Assessment form steps
    step1: te("1. Farm & Location", "1. పొలం & భూగోళం"),
    step2: te("2. Soil Chemistry", "2. నేల రసాయనాలు"),
    step3: te("3. Weather Context", "3. వాతావరణం"),
    step4: te("4. Cropping Notes", "4. పంట గమనికలు"),

    // Labels
    farmNameLbl: te("Farm / Holding Name", "పొలం పేరు"),
    districtLbl: te("District", "జిల్లా"),
    stateLbl: te("State", "రాష్ట్రం"),
    acreageLbl: te("Land Area (Acres)", "సాగు విస్తీర్ణం (ఎకరాలు)"),
    seasonLbl: te("Agricultural Season", "వ్యవసాయ సీజన్"),
    irrigationLbl: te("Irrigation Method", "నీటి పారుదల విధానం"),
    waterLbl: te("Water Availability", "నీటి లభ్యత"),
    nLbl: te("Nitrogen (N) kg/ha", "నత్రజని (N) కిగ్రా/హె"),
    pLbl: te("Phosphorus (P) kg/ha", "భాస్వరం (P) కిగ్రా/హె"),
    kLbl: te("Potassium (K) kg/ha", "పొటాష్ (K) కిగ్రా/హె"),
    phLbl: te("Soil pH (0 – 14)", "నేల pH (0 – 14)"),
    tempLbl: te("Temperature (°C)", "ఉష్ణోగ్రత (°C)"),
    humidityLbl: te("Relative Humidity (%)", "తేమ శాతం (%)"),
    rainfallLbl: te("Seasonal Rainfall (mm)", "సీజనల్ వర్షపాతం (mm)"),
    prevCropsLbl: te("Previous Crops Grown", "గతంలో వేసిన పంటలు"),
    prefLbl: te(
      "Farmer Preferences / Soil Notes",
      "రైతు ప్రాధాన్యతలు / నేల గమనికలు"
    ),
    soilCardSubtitle: te(
      "Enter values from your certified Soil Health Card or soil lab report.",
      "మీ సాయిల్ హెల్త్ కార్డు లేదా ల్యాబ్ నివేదిక నుండి విలువలు నమోదు చేయండి."
    ),

    // Buttons
    fetchWeatherBtn: te("Fetch live district weather", "జిల్లా వాతావరణం పొందండి"),
    fetchingBtn: te("Connecting to Open-Meteo…", "ఓపెన్-మెటియో కి కనెక్ట్ అవుతున్నాం…"),
    nextBtn: te("Continue", "కొనసాగించండి"),
    backBtn: te("Back", "వెనుకకు"),
    submitBtn: te("Run Verified Farm Assessment", "ధృవీకరించిన అంచనా ప్రారంభించండి"),
    submittingBtn: te("Executing Random Forest…", "రాండమ్ ఫారెస్ట్ విశ్లేషిస్తోంది…"),

    // Results
    assessmentDone: te(
      "Assessment Completed & Verified",
      "అంచనా పూర్తయింది & ధృవీకరించబడింది"
    ),
    exportBtn: te("Generate PDF Report", "PDF నివేదిక తయారు చేయండి"),
    confidenceLbl: te("Model Confidence", "మోడల్ విశ్వసనీయత"),
    altsTitle: te("Alternative Suitable Crops", "ప్రత్యామ్నాయ పంటలు"),
    advisorHeading: te("Scientific Agricultural Advisory", "శాస్త్రీయ వ్యవసాయ సలహా"),
    soilHealthTitle: te("Soil Health & pH Status", "నేల ఆరోగ్యం & pH స్థితి"),
    cropMgtTitle: te("Crop Management Practices", "పంట నిర్వహణ పద్ధతులు"),
    waterMgtTitle: te("Water & Irrigation Guidance", "నీటి పారుదల సూచనలు"),
    riskTitle: te("Seasonal Risk Management", "సీజనల్ రిస్క్ నిర్వహణ"),
    storageNotice: te(
      "Storage: In-Memory Session — Assessments are not persisted across server restarts. Configure Supabase for persistence.",
      "నిల్వ: ఇన్-మెమరీ సెషన్ — సర్వర్ రీస్టార్ట్ అయితే డేటా తొలగించబడుతుంది. సుపాబేస్ అమర్చండి."
    ),

    // Modal
    modalTitle: te("Confirm Assessment Report Export", "PDF నివేదిక నిర్ధారించండి"),
    confirmBtn: te("Confirm & Download PDF", "నిర్ధారించి డౌన్‌లోడ్ చేయండి"),
    cancelBtn: te("Cancel", "రద్దు చేయండి"),
    compilingPdf: te("Compiling PDF…", "PDF తయారుచేస్తున్నాం…"),

    // Dashboard cards
    dashSoilCard: te("Soil Profile", "నేల సమాచారం"),
    dashWeatherCard: te("Current Weather", "ప్రస్తుత వాతావరణం"),
    dashTasksCard: te("Suggested Next Steps", "సూచించిన తదుపరి చర్యలు"),
    dashModelsCard: te("Model Registry Status", "మోడల్ రిజిస్ట్రీ స్థితి"),
    dashHistoryCard: te("Recent Assessments", "తాజా అంచనాలు"),
    runAssessmentBtn: te("Run New Assessment", "కొత్త అంచనా వేయండి"),
    noAssessmentYet: te("No assessment yet", "ఇంకా అంచనా లేదు"),
    noAssessmentDesc: te(
      "Run a farm assessment to see soil health, crop recommendations, and advisory here.",
      "నేల ఆరోగ్యం, పంట సిఫార్సులు మరియు సలహా చూడటానికి పొలం అంచనా వేయండి."
    ),

    // Chatbot
    chatTitle: te("Rythu AI Assistant", "రైతు AI సహాయకుడు"),
    chatSub: te("Bilingual Agronomic Advisory", "ద్విభాషా వ్యవసాయ సలహాదారు"),
    chatPlaceholder: te("Ask a question about your farm...", "మీ పొలం గురించి ఏదైనా అడగండి..."),
    chatQuick1: te("What crop should I grow?", "నా నేలకు ఏ పంట ఉత్తమం?"),
    chatQuick2: te("How to improve soil pH?", "నేల pH ఎలా మెరుగుపరచాలి?"),
    chatQuick3: te("Irrigation advice for my farm", "నా పొలానికి సాగునీటి నిర్వహణ"),
    chatQuick4: te("Fertilizer dosage for cotton", "పత్తి పంటకు ఎరువుల మోతాదు"),
    chatDisclaimer: te(
      "AI advice is for guidance only. Verify with local agricultural extension officers (RBK/KVK).",
      "AI సలహా మార్గదర్శకత్వం కొరకు మాత్రమే. స్థానిక వ్యవసాయ అధికారులతో (RBK/KVK) సంప్రదించండి."
    ),

    // Upload
    uploadSoilReportTitle: te("Upload Soil Health Report", "సాయిల్ హెల్త్ కార్డు / ల్యాబ్ రిపోర్ట్ అప్‌లోడ్"),
    uploadFieldPhotoTitle: te("Upload Field Photo", "పొలం ఫోటో అప్‌లోడ్"),
    uploadCropPhotoTitle: te("Upload Crop Photo", "పంట ఫోటో అప్‌లోడ్"),
    uploadHint: te("Supports PDF, JPG, PNG, WEBP (Max 10MB)", "PDF, JPG, PNG, WEBP కి మద్దతు (గరిష్టం 10MB)"),
    uploadDrop: te("Drag & drop files or click to browse", "ఫైళ్ళను లాగండి లేదా బ్రౌజ్ చేయడానికి క్లిక్ చేయండి"),
    uploading: te("Uploading and verifying...", "అప్‌లోడ్ చేసి ధృవీకరిస్తున్నాం..."),
    uploadedFilesTitle: te("Uploaded Farm Documents & Photos", "అప్‌లోడ్ చేసిన పత్రాలు & ఫోటోలు"),
    deleteFile: te("Delete", "తొలగించు"),
  };
}

/* ── File Upload Helper Component ── */
function FileUploadBox({
  category,
  title,
  subtitle,
  accept = ".pdf,.jpg,.jpeg,.png,.webp",
  onUpload,
  uploading,
  files,
  onDelete,
  language,
}: {
  category: "soil_report" | "field_photo" | "crop_photo";
  title: string;
  subtitle: string;
  accept?: string;
  onUpload: (category: "soil_report" | "field_photo" | "crop_photo", file: File) => void;
  uploading: boolean;
  files: UploadedFileItem[];
  onDelete: (fileId: string) => void;
  language: Lang;
}) {
  const categoryFiles = files.filter((f) => f.category === category);
  const inputId = `file-input-${category}`;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(category, e.target.files[0]);
      e.target.value = "";
    }
  };

  return (
    <div className="upload-section" style={{ marginTop: 12 }}>
      <label htmlFor={inputId} className="upload-zone" style={{ display: "block" }}>
        <input
          id={inputId}
          type="file"
          accept={accept}
          style={{ display: "none" }}
          disabled={uploading}
          onChange={handleFileChange}
        />
        <div className="upload-zone-icon">
          {category === "soil_report" ? <UploadIcon size={24} /> : <ImageIcon size={24} />}
        </div>
        <div className="upload-zone-title">{title}</div>
        <div className="upload-zone-hint">
          {uploading
            ? (language === "te" ? "అప్‌లోడ్ చేసి ధృవీకరిస్తున్నాం..." : "Uploading & verifying...")
            : subtitle}
        </div>
      </label>

      {categoryFiles.length > 0 && (
        <div style={{ marginTop: 10 }}>
          {categoryFiles.map((file) => (
            <div key={file.file_id} className="upload-file-item">
              <span style={{ color: "var(--green-700)" }}>
                {file.file_type === "pdf" ? <FileTextIcon size={18} /> : <ImageIcon size={18} />}
              </span>
              <div className="upload-file-info">
                <div className="upload-file-name">{file.original_filename}</div>
                <div className="upload-file-size">
                  {Math.round(file.size_bytes / 1024)} KB · {file.storage === "supabase" ? "Supabase Cloud" : "Local Temp Storage"}
                </div>
              </div>
              <span className="upload-file-status success">✓ Verified</span>
              <button
                type="button"
                className="upload-remove-btn"
                title="Remove"
                onClick={() => onDelete(file.file_id)}
              >
                <TrashIcon size={15} />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const DEFAULT_POPULAR_COMMODITIES = [
  { name: "Rice", name_te: "వరి", category: "Cereal" },
  { name: "Wheat", name_te: "గోధుమ", category: "Cereal" },
  { name: "Cotton", name_te: "పత్తి", category: "Fiber" },
  { name: "Maize", name_te: "మొక్కజొన్న", category: "Cereal" },
  { name: "Dry Chillies", name_te: "ఎండు మిర్చి", category: "Spices" },
  { name: "Groundnut", name_te: "వేరుశెనగ", category: "Oilseed" },
  { name: "Turmeric", name_te: "పసుపు", category: "Spices" },
  { name: "Tomato", name_te: "టమాటా", category: "Vegetable" },
  { name: "Onion", name_te: "ఉల్లిపాయ", category: "Vegetable" },
  { name: "Potato", name_te: "బంగాళాదుంప", category: "Vegetable" },
  { name: "Bengal Gram(Gram)(Whole)", name_te: "శనగలు", category: "Pulse" },
  { name: "Green Gram (Moong)(Whole)", name_te: "పెసలు", category: "Pulse" },
  { name: "Black Gram (Urd Beans)(Whole)", name_te: "మినుములు", category: "Pulse" },
  { name: "Mustard", name_te: "ఆవాలు", category: "Oilseed" },
  { name: "Soyabean", name_te: "సోయాబీన్", category: "Oilseed" },
  { name: "Sugarcane", name_te: "చెరకు", category: "Commercial" },
  { name: "Coriander(Leaves)", name_te: "కొత్తిమీర", category: "Spices" },
  { name: "Garlic", name_te: "వెల్లుల్లి", category: "Spices" },
  { name: "Ginger(Dry)", name_te: "అల్లం / శొంఠి", category: "Spices" },
  { name: "Castor Seed", name_te: "ఆముదాలు", category: "Oilseed" },
];

const DEFAULT_POPULAR_MANDIS = [
  { name: "Varanasi(Grain)", state: "Uttar Pradesh", district: "Varanasi" },
  { name: "Guntur", state: "Andhra Pradesh", district: "Guntur" },
  { name: "Tenali", state: "Andhra Pradesh", district: "Guntur" },
  { name: "Kurnool", state: "Andhra Pradesh", district: "Kurnool" },
  { name: "Chittoor", state: "Andhra Pradesh", district: "Chittoor" },
  { name: "Nizamabad", state: "Telangana", district: "Nizamabad" },
  { name: "Warangal", state: "Telangana", district: "Warangal" },
  { name: "Lasalgaon", state: "Maharashtra", district: "Nashik" },
  { name: "Nagpur Apmc", state: "Maharashtra", district: "Nagpur" },
  { name: "Rajkot", state: "Gujarat", district: "Rajkot" },
  { name: "Indore", state: "Madhya Pradesh", district: "Indore" },
  { name: "Agra", state: "Uttar Pradesh", district: "Agra" },
  { name: "Khanna", state: "Punjab", district: "Ludhiana" },
  { name: "Suryapet", state: "Telangana", district: "Suryapet" },
  { name: "Khammam", state: "Telangana", district: "Khammam" },
  { name: "Bowenpally", state: "Telangana", district: "Hyderabad" },
];

/* ══════════════════════════════════════════════════════════════
   MAIN COMPONENT
══════════════════════════════════════════════════════════════ */
export default function DashboardPage() {
  const router = useRouter();
  const { user: globalUser, loading: authChecking, logout: globalLogout, token: globalToken, handleAuthSuccess } = useAuth();
  const { registerScreen } = useScreenContext();
  const _lastScreenRef = useRef<string>("");

  // Authentication Route Guard: require valid session to access dashboard
  useEffect(() => {
    if (!authChecking && !globalUser) {
      router.replace("/login?redirect=/dashboard");
    }
  }, [authChecking, globalUser, router]);
  const [language, setLanguage] = useState<Lang>("en");
  const [view, setView] = useState<View>("dashboard");

  // Synchronize view with URL param if present (e.g. ?view=disease or #disease)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const targetView = params.get("view") || (window.location.hash ? window.location.hash.replace("#", "") : null);
      if (
        targetView &&
        [
          "dashboard",
          "assessment",
          "recommendations",
          "weather",
          "soil",
          "irrigation",
          "market",
          "disease",
          "reports",
          "registry",
          "settings",
        ].includes(targetView)
      ) {
        setView(targetView as View);
      }
    }
  }, []);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const t = useTranslations(language);

  // Assessment results
  const [result, setResult] = useState<Assessment | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeStep, setActiveStep] = useState(1);

  // Model catalog
  const [modelCatalog, setModelCatalog] = useState<ModelCatalogEntry[]>([]);
  const [verifyingModels, setVerifyingModels] = useState(false);

  // Current weather for dashboard
  const [dashWeather, setDashWeather] = useState<{
    temp?: number;
    humidity?: number;
    rainfall?: number;
    source?: string;
    district?: string;
  } | null>(null);

  // Form state
  const [farmName, setFarmName] = useState("");
  const [district, setDistrict] = useState("");
  const [state, setState] = useState("");
  const [acreage, setAcreage] = useState("");
  const [season, setSeason] = useState("Kharif");
  const [irrigation, setIrrigation] = useState("Drip");
  const [water, setWater] = useState("Borewell");
  const [savedFarmProfile, setSavedFarmProfile] = useState<FarmProfile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileEditing, setProfileEditing] = useState(false);
  const [profileNotice, setProfileNotice] = useState("");
  const [nitrogen, setNitrogen] = useState("90");
  const [phosphorus, setPhosphorus] = useState("42");
  const [potassium, setPotassium] = useState("43");
  const [ph, setPh] = useState("6.5");
  const [temp, setTemp] = useState("");
  const [humidity, setHumidity] = useState("");
  const [rainfall, setRainfall] = useState("");
  const [weatherNotice, setWeatherNotice] = useState("");
  const [weatherSourcePill, setWeatherSourcePill] = useState("");
  const [fetchingWeather, setFetchingWeather] = useState(false);
  const [prevCrops, setPrevCrops] = useState("Paddy, Cotton");
  const [preferences, setPreferences] = useState("");

  // Report modal
  const [showReportModal, setShowReportModal] = useState(false);
  const [reportPreview, setReportPreview] = useState<ReportPreview | null>(null);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [pdfError, setPdfError] = useState("");

  const [apiUrl, setApiUrl] = useState<string>(() => getApiBaseUrl());

  const refreshModelCatalog = useCallback(async () => {
    if (!apiUrl) return;
    setVerifyingModels(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/models`);
      if (!response.ok) throw new Error("The model registry is unavailable.");
      setModelCatalog(await response.json());
    } finally { setVerifyingModels(false); }
  }, [apiUrl]);

  const applyFarmProfile = useCallback((profile: FarmProfile) => {
    setFarmName(profile.farm_name); setDistrict(profile.district); setState(profile.state);
    setAcreage(String(profile.acreage)); setSeason(profile.season);
    setIrrigation(profile.irrigation_method); setWater(profile.water_availability);
  }, []);

  const selectState = (nextState: string) => {
    setState(nextState);
    if (district && !INDIA_LOCATIONS[nextState]?.includes(district)) setDistrict("");
  };

  const districtChoices = state ? INDIA_LOCATIONS[state] ?? [] : [];

  const fetchFarmProfile = useCallback(async () => {
    if (!globalUser || !apiUrl) return;
    setProfileLoading(true); setProfileNotice("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/farm-profile`, {
        headers: globalToken ? { Authorization: `Bearer ${globalToken}` } : {},
        credentials: "include",
      });
      if (response.status === 404) { setSavedFarmProfile(null); return; }
      if (!response.ok) throw new Error("Could not load the saved farm profile.");
      const profile: FarmProfile = await response.json();
      setSavedFarmProfile(profile); applyFarmProfile(profile);
    } catch (err) {
      setProfileNotice(err instanceof Error ? err.message : "Could not load the saved farm profile.");
    } finally { setProfileLoading(false); }
  }, [apiUrl, applyFarmProfile, globalToken, globalUser]);

  const saveFarmProfile = async () => {
    setProfileNotice("");
    const profile = { farm_name: farmName.trim(), district: district.trim(), state: state.trim(), acreage: Number(acreage), season: season.trim(), irrigation_method: irrigation.trim(), water_availability: water.trim() };
    if (!profile.farm_name || !profile.district || !profile.state || !profile.season || !profile.irrigation_method || !profile.water_availability || !Number.isFinite(profile.acreage) || profile.acreage <= 0) {
      setProfileNotice("Complete every farm field and enter a valid land area before saving."); return;
    }
    setProfileSaving(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/farm-profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(globalToken ? { Authorization: `Bearer ${globalToken}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify(profile),
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "Could not save the farm profile.");
      setSavedFarmProfile(data); applyFarmProfile(data); setProfileEditing(false); setProfileNotice("Farm profile saved securely to your account.");
    } catch (err) { setProfileNotice(err instanceof Error ? err.message : "Could not save the farm profile."); }
    finally { setProfileSaving(false); }
  };

  // Saved Assessments & Persistence
  const [savedAssessments, setSavedAssessments] = useState<Assessment[]>([]);

  const fetchAssessments = useCallback(async () => {
    if (!apiUrl) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/assessments`, {
        headers: globalToken ? { Authorization: `Bearer ${globalToken}` } : {},
        credentials: "include",
      });
      if (res.ok) {
        const data: Assessment[] = await res.json();
        setSavedAssessments(data);
        if (data && data.length > 0) {
          const completed = data.find((a) => (a.results || []).some((r) => r.model_id === "crop-recommendation-v1" && r.prediction));
          const target = completed || data[0];
          setResult((prev) => prev || target);
          if (target.input) {
            if (target.input.farm_name) setFarmName((prev) => prev || target.input.farm_name);
            if (target.input.district) setDistrict((prev) => prev || target.input.district);
            if (target.input.state) setState((prev) => prev || target.input.state);
            if (target.input.acreage) setAcreage((prev) => prev || String(target.input.acreage));
            if (target.input.season) setSeason((prev) => prev || target.input.season);
            if (target.input.irrigation_type) setIrrigation((prev) => prev || target.input.irrigation_type);
            if (target.input.water_availability) setWater((prev) => prev || target.input.water_availability);
            if (target.input.soil) {
              if (target.input.soil.nitrogen_kg_ha != null) setNitrogen(String(target.input.soil.nitrogen_kg_ha));
              if (target.input.soil.phosphorus_kg_ha != null) setPhosphorus(String(target.input.soil.phosphorus_kg_ha));
              if (target.input.soil.potassium_kg_ha != null) setPotassium(String(target.input.soil.potassium_kg_ha));
              if (target.input.soil.ph != null) setPh(String(target.input.soil.ph));
            }
          }
        }
      }
    } catch {
      // offline or server starting
    }
  }, [apiUrl, globalToken]);

  // Uploaded Files State
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileItem[]>([]);
  const [uploadingCategory, setUploadingCategory] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [uploadSuccessMsg, setUploadSuccessMsg] = useState("");

  const fetchUploads = useCallback(async () => {
    if (!apiUrl) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/uploads`, {
        headers: globalToken ? { Authorization: `Bearer ${globalToken}` } : {},
        credentials: "include",
      });
      if (res.ok) {
        const data: UploadedFileItem[] = await res.json();
        setUploadedFiles(data);
      }
    } catch {
      // ignore
    }
  }, [apiUrl, globalToken]);

  async function handleFileUpload(
    category: "soil_report" | "field_photo" | "crop_photo",
    file: File
  ) {
    setUploadError("");
    setUploadingCategory(category);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${apiUrl}/api/v1/uploads/${category}`, {
        method: "POST",
        headers: globalToken ? { Authorization: `Bearer ${globalToken}` } : {},
        body: formData,
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Upload failed (HTTP ${res.status})`);
      }
      const data: UploadedFileItem = await res.json();
      setUploadedFiles((prev) => [data, ...prev.filter((f) => f.file_id !== data.file_id)]);
      setUploadSuccessMsg(
        language === "te"
          ? `${data.original_filename} విజయవంతంగా అప్‌లోడ్ చేయబడింది.`
          : `${data.original_filename} successfully uploaded and verified.`
      );
      setTimeout(() => setUploadSuccessMsg(""), 4000);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploadingCategory(null);
    }
  }

  async function handleDeleteUpload(fileId: string) {
    try {
      const res = await fetch(`${apiUrl}/api/v1/uploads/${fileId}`, {
        method: "DELETE",
        headers: globalToken ? { Authorization: `Bearer ${globalToken}` } : {},
        credentials: "include",
      });
      if (res.ok) {
        setUploadedFiles((prev) => prev.filter((f) => f.file_id !== fileId));
      }
    } catch {
      // ignore
    }
  }

  // Chatbot State
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMinimized, setChatMinimized] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    if (chatMessages.length === 0) {
      setChatMessages([
        {
          sender: "bot",
          text:
            language === "te"
              ? "నమస్కారం! నేను మీ క్షేత్రAI వ్యవసాయ సహాయకుడిని. మీ నేల, వాతావరణం, పంట సిఫార్సులు, ఎరువుల నిర్వహణ గురించి నన్ను అడగండి."
              : "Namaste! I am your KshetraIQ Agronomic Assistant. Ask me about crop recommendations, soil health, irrigation advice, or fertilizer management for your farm.",
        },
      ]);
    }
  }, [language, chatMessages.length]);

  async function handleSendMessage(msgToSend?: string) {
    const text = (msgToSend || chatInput).trim();
    if (!text || chatLoading) return;

    const userMessage: ChatMessage = { sender: "user", text };
    setChatMessages((prev) => [...prev, userMessage]);
    setChatInput("");
    setChatLoading(true);

    try {
      const res = await fetch(`${apiUrl}/api/v1/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(globalToken ? { Authorization: `Bearer ${globalToken}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({
          message: text,
          language,
          assessment_id: result?.assessment_id || null,
          screen_context: {
            screen_id: view,
            screen_title: _pageTitles[view] || view,
            route: "/dashboard",
            selected_crop: result?.results?.find((r: any) => r.model_id === "crop-recommendation-v1")?.message?.split(/\s+/)[0] || null,
            displayed_data: _screenData,
            active_tab: view,
          },
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Error ${res.status}`);
      }

      const data = await res.json();
      setChatMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text: data.reply,
          mode: data.mode,
          disclaimer: data.disclaimer,
          contextUsed: data.assessment_context_used,
        },
      ]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text:
            language === "te"
              ? "క్షమించండి, సర్వర్ నుండి సమాధానం పొందలేకపోయాము. బ్యాకెండ్ నడుస్తున్నదో లేదో సరిచూసుకోండి."
              : "Apologies, I encountered an error communicating with the agronomic intelligence service. Please ensure the backend is connected.",
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  // Voice Input (Web Speech API) & TTS (SpeechSynthesis)
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speechRecognitionSupported, setSpeechRecognitionSupported] = useState(true);

  // Storage and LLM metadata from backend
  const [storageMode, setStorageMode] = useState<string>("sqlite_local");
  const [llmConfigured, setLlmConfigured] = useState<boolean>(false);
  const [llmProviderName, setLlmProviderName] = useState<string>("none");

  // Additional ML Predictions
  const [yieldCrop, setYieldCrop] = useState<string>("Rice");
  const [yieldResult, setYieldResult] = useState<any>(null);
  const [yieldLoading, setYieldLoading] = useState<boolean>(false);
  const [yieldError, setYieldError] = useState<string>("");

  const [climateResult, setClimateResult] = useState<any>(null);
  const [climateLoading, setClimateLoading] = useState<boolean>(false);
  const [climateError, setClimateError] = useState<string>("");

  const [sustainabilityResult, setSustainabilityResult] = useState<any>(null);
  const [sustainabilityLoading, setSustainabilityLoading] = useState<boolean>(false);
  const [sustainabilityError, setSustainabilityError] = useState<string>("");

  const [weatherRiskResult, setWeatherRiskResult] = useState<any>(null);
  const [weatherRiskLoading, setWeatherRiskLoading] = useState<boolean>(false);
  const [weatherRiskError, setWeatherRiskError] = useState<string>("");

  // ──── Authentication State ────
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [authUser, setAuthUser] = useState<{ user_id: string; email: string; display_name: string; created_at: string } | null>(null);

  useEffect(() => {
    if (globalUser) {
      setAuthUser((prev) => {
        if (
          prev &&
          prev.user_id === globalUser.user_id &&
          prev.email === globalUser.email &&
          prev.display_name === globalUser.full_name
        ) {
          return prev;
        }
        return {
          user_id: globalUser.user_id,
          email: globalUser.email,
          display_name: globalUser.full_name,
          created_at: globalUser.created_at,
        };
      });
      setAuthToken((prev) => (prev === globalToken ? prev : globalToken));
    } else {
      setAuthUser(null);
      setAuthToken(null);
      setSavedFarmProfile(null);
      setProfileEditing(false);
      setProfileNotice("");
    }
  }, [globalUser, globalToken]);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authTab, setAuthTab] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authDisplayName, setAuthDisplayName] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  // ──── Market Price State ────
  const [mktCommodity, setMktCommodity] = useState("Wheat");
  const [mktMandi, setMktMandi] = useState("Varanasi(Grain)");
  const [marketCatalog, setMarketCatalog] = useState<{
    popular_commodities: { name: string; name_te: string; category: string }[];
    popular_mandis: { name: string; state: string; district: string }[];
    verified_pairs?: { commodity: string; mandi: string; state: string; district: string; source: string }[];
  } | null>(null);

  const fetchMarketCatalog = useCallback(async () => {
    if (!apiUrl) return;
    try {
      const res = await fetch(`${apiUrl}/api/v1/market/commodities`);
      if (res.ok) {
        const data = await res.json();
        // Never replace the known catalogue with an incomplete response.
        // A transient backend/model start-up issue must not collapse the picker
        // to a single commodity.
        if (Array.isArray(data?.popular_commodities) && data.popular_commodities.length > 0) {
          setMarketCatalog(data);
        }
      }
    } catch {
      // offline or server starting
    }
  }, [apiUrl]);

  // The model vocabulary is broader than locally verified observation
  // coverage.  When the catalogue is available, keep the picker on an exact
  // pair that can be anchored to a real live/cache/benchmark observation.
  const verifiedMandisForCommodity = useMemo(() => {
    const pairs = marketCatalog?.verified_pairs || [];
    return pairs.filter((pair) => pair.commodity.toLowerCase() === mktCommodity.toLowerCase());
  }, [marketCatalog, mktCommodity]);

  const marketMandiOptions = verifiedMandisForCommodity.length > 0
    ? verifiedMandisForCommodity.map(({ mandi, district, state }) => ({ name: mandi, district, state }))
    : (marketCatalog?.popular_mandis || DEFAULT_POPULAR_MANDIS);

  useEffect(() => {
    if (verifiedMandisForCommodity.length > 0 && !verifiedMandisForCommodity.some((pair) => pair.mandi === mktMandi)) {
      setMktMandi(verifiedMandisForCommodity[0].mandi);
      setMktResult(null);
      setMktError("");
    }
  }, [verifiedMandisForCommodity, mktMandi]);
  const [mktDaysAhead, setMktDaysAhead] = useState("7");
  const [mktResult, setMktResult] = useState<any>(null);
  const [mktLoading, setMktLoading] = useState(false);
  const [mktError, setMktError] = useState("");

  // ──── Soil Health Score State ────
  const [soilScoreResult, setSoilScoreResult] = useState<any>(null);
  const [calculatingSoilScore, setCalculatingSoilScore] = useState(false);
  const [soilScoreError, setSoilScoreError] = useState("");

  // ──── Plant Disease State ────
  const [diseaseFile, setDiseaseFile] = useState<File | null>(null);
  const [diseasePreviewUrl, setDiseasePreviewUrl] = useState<string | null>(null);
  const [diseaseResult, setDiseaseResult] = useState<any>(null);
  const [diseaseLoading, setDiseaseLoading] = useState(false);
  const [diseaseError, setDiseaseError] = useState("");
  const [plantAnalysis, setPlantAnalysis] = useState<any>(null);
  const [plantModelStatus, setPlantModelStatus] = useState<any[]>([]);
  const [plantReportLoading, setPlantReportLoading] = useState(false);

  async function handleDownloadPlantReport(aid?: string) {
    const targetId = aid || plantAnalysis?.analysis_id;
    if (!targetId) return;
    setPlantReportLoading(true);
    try {
      const res = await fetch(`${apiUrl}/api/plant-intelligence/${targetId}/report`, {
        method: "POST",
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || "Plant report generation failed.");
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `plant_intelligence_report_${targetId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      alert(`Could not download report: ${e.message}`);
    } finally {
      setPlantReportLoading(false);
    }
  }

  useEffect(() => {
    fetch(`${apiUrl}/api/plant-intelligence/models/status`, {
      headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
      credentials: "include",
    }).then(async (response) => {
      const payload: unknown = await response.json().catch(() => null);
      if (response.ok && Array.isArray(payload)) setPlantModelStatus(payload);
    }).catch(() => undefined);
  }, [apiUrl, authToken]);

  // ──── Irrigation Calculator State ────
  const [irrCrop, setIrrCrop] = useState("Rice");
  const [irrCropDays, setIrrCropDays] = useState("45");
  const [irrSoilMoisture, setIrrSoilMoisture] = useState("320");
  const [irrSoilType, setIrrSoilType] = useState("Loam");
  const [irrTemp, setIrrTemp] = useState("28");
  const [irrRainfallForecast, setIrrRainfallForecast] = useState("0");
  const [irrSoilTemp, setIrrSoilTemp] = useState("24");
  const [irrHumidity, setIrrHumidity] = useState("60");
  const [irrAreaAcres, setIrrAreaAcres] = useState("2.5");
  const [irrForceDeterministic, setIrrForceDeterministic] = useState(false);
  const [irrResult, setIrrResult] = useState<any>(null);
  const [irrLoading, setIrrLoading] = useState(false);
  const [irrError, setIrrError] = useState("");

  // ── Screen Context Registration ──────────────────────────────────────────────
  // Build structured displayed_data for the active view.
  // useMemo ensures a new object is only created when the actual values change.
  // All state variables are declared ABOVE this point.
  const _screenData = useMemo(() => {
    const base: Record<string, any> = {
      view,
      farm_name: farmName || savedFarmProfile?.farm_name || "",
      district: district || savedFarmProfile?.district || "",
      state: state || savedFarmProfile?.state || "",
      acreage: acreage || savedFarmProfile?.acreage || "",
      season: season || savedFarmProfile?.season || "Kharif",
    };

    if (view === "dashboard") {
      base.soil_health_score = result?.advisor?.soil_health_assessment?.score;
      base.soil_health_category = result?.advisor?.soil_health_assessment?.category;
      base.weather_temp = dashWeather?.temp;
      base.weather_humidity = dashWeather?.humidity;
      base.weather_rainfall = dashWeather?.rainfall;
      base.models_verified = modelCatalog.filter(
        (m) => (m.readiness_status ?? m.contract_status) === "VERIFIED" ||
                (m.readiness_status ?? m.contract_status) === "verified"
      ).length;
      base.models_total = modelCatalog.length;
      base.recommended_crop = result?.results?.find((r: any) => r.model_id === "crop-recommendation-v1")?.message?.split(" ")[0];
    } else if (view === "soil") {
      base.nitrogen = nitrogen;
      base.phosphorus = phosphorus;
      base.potassium = potassium;
      base.ph = ph;
      base.temperature = temp;
      base.humidity = humidity;
      base.rainfall = rainfall;
      base.soil_health_score = soilScoreResult?.score ?? (result as any)?.advisor?.soil_health_assessment?.score;
      base.soil_health_category = soilScoreResult?.category ?? (result as any)?.advisor?.soil_health_assessment?.category;
    } else if (view === "assessment" || view === "recommendations" || view === "results") {
      const cropRec = result?.results?.find((r: any) => r.model_id === "crop-recommendation-v1");
      base.recommended_crop = cropRec?.message?.split(/\s+/)[0] || "N/A";
      base.assessment_id = result?.assessment_id;
      base.nitrogen = nitrogen;
      base.phosphorus = phosphorus;
      base.potassium = potassium;
      base.ph = ph;
      base.temperature = temp;
      base.humidity = humidity;
      base.season = season;
      base.active_step = activeStep;
    } else if (view === "weather") {
      base.current_temp = temp || dashWeather?.temp;
      base.current_humidity = humidity || dashWeather?.humidity;
      base.current_rainfall = rainfall || dashWeather?.rainfall;
      base.weather_source = dashWeather?.source;
      base.weather_district = dashWeather?.district || district;
    } else if (view === "irrigation") {
      base.irr_crop = irrCrop;
      base.irr_crop_days = irrCropDays;
      base.irr_soil_moisture = irrSoilMoisture;
      base.irr_soil_type = irrSoilType;
      base.irr_temp = irrTemp;
      base.irr_humidity = irrHumidity;
      base.irr_rainfall_forecast = irrRainfallForecast;
      base.irr_area_acres = irrAreaAcres;
      if (irrResult) {
        base.irrigation_recommendation = (irrResult as any).recommendation || (irrResult as any).ppo_action;
        base.water_requirement_mm = (irrResult as any).water_requirement_mm;
        base.application_depth_mm = (irrResult as any).application_depth_mm;
        base.next_irrigation = (irrResult as any).next_irrigation_date;
      }
    } else if (view === "market") {
      base.commodity = mktCommodity;
      base.mandi = mktMandi;
      base.days_ahead = mktDaysAhead;
      if (mktResult) {
        base.forecast_modal_price = (mktResult as any).forecast_modal_price;
        base.observed_market_price = (mktResult as any).observed_modal_price;
        base.observation_date = (mktResult as any).observation_date;
        base.trend_direction = (mktResult as any).trend_direction;
        base.primary_forecast_method = (mktResult as any).primary_forecast_method;
        base.seasonal_reference_price = (mktResult as any).seasonal_reference_price;
      }
    } else if (view === "disease") {
      base.disease_file = diseaseFile?.name;
      if (plantAnalysis) {
        base.analysis_id = plantAnalysis.analysis_id;
        base.sam_status = plantAnalysis.executed_models?.sam?.status;
        base.lime_status = plantAnalysis.executed_models?.lime?.status;
        base.blip_caption = plantAnalysis.executed_models?.blip?.result?.caption;
        base.blip_detailed_description =
          plantAnalysis.executed_models?.blip?.result?.detailed_caption ||
          plantAnalysis.executed_models?.blip?.result?.full_description ||
          plantAnalysis.executed_models?.blip?.result?.caption;
      }
      if (diseaseResult) {
        base.disease_label = (diseaseResult as any).predicted_class || (diseaseResult as any).label;
        base.disease_label_te = (diseaseResult as any).label_te;
        base.confidence_pct = (diseaseResult as any).confidence_pct;
        base.is_healthy = (diseaseResult as any).is_healthy;
        base.recommended_mitigation = (diseaseResult as any).recommended_mitigation;
        base.crop_affected = (diseaseResult as any).crop;
      }
    } else if (view === "reports") {
      base.saved_assessments_count = savedAssessments?.length || 0;
      base.has_report = !!result;
    } else if (view === "registry") {
      base.models_count = modelCatalog.length;
      base.verified_count = modelCatalog.filter(
        (m) => (m.readiness_status ?? m.contract_status) === "VERIFIED" ||
                (m.readiness_status ?? m.contract_status) === "verified"
      ).length;
      base.model_ids = modelCatalog.map((m) => m.model_id).join(", ");
    } else if (view === "profile") {
      base.farmer_name = authUser?.display_name || savedFarmProfile?.farm_name;
      base.farmer_email = authUser?.email;
      base.farm_size = acreage || savedFarmProfile?.acreage;
      base.active_crop = season;
    }

    // Strip empty/undefined values so the JSON payload is clean
    return Object.fromEntries(
      Object.entries(base).filter(([, v]) => v !== undefined && v !== null && v !== "")
    );
  }, [
    view, farmName, district, state, acreage, season,
    savedFarmProfile, result, dashWeather, modelCatalog,
    nitrogen, phosphorus, potassium, ph, temp, humidity, rainfall,
    activeStep,
    irrCrop, irrCropDays, irrSoilMoisture, irrSoilType, irrTemp,
    irrHumidity, irrRainfallForecast, irrAreaAcres, irrResult,
    mktCommodity, mktMandi, mktDaysAhead, mktResult,
    diseaseFile, diseaseResult, plantAnalysis,
    savedAssessments, authUser,
    soilScoreResult,
  ]);

  // Screen titles per view — useMemo so the object reference is stable
  const _pageTitles = useMemo<Record<string, string>>(() => ({
    dashboard: t.navDashboard || "Farm Dashboard",
    soil: t.navSoil || "Soil Health",
    assessment: "Farm Assessment",
    recommendations: "Crop Recommendations",
    results: "Assessment Results",
    weather: t.navWeather || "Weather Intelligence",
    irrigation: t.navIrrigation || "Irrigation Management",
    market: t.navMarket || "Market Intelligence",
    disease: t.navDisease || "Plant Disease Detection",
    reports: t.navReports || "Farm Reports",
    registry: t.navModelRegistry || "AI Model Registry",
    profile: t.navProfile || "Farm Profile",
    settings: "Settings",
  }), [t]);

  // Register active screen — only fires when serialized context actually changes
  useEffect(() => {
    const selectedCrop = result?.results
      ?.find((r: any) => r.model_id === "crop-recommendation-v1")
      ?.message?.split(/\s+/)[0];
    const payload = {
      screenId: view,
      title: _pageTitles[view] || view,
      selectedCrop,
      data: _screenData,
    };
    const serialized = JSON.stringify(payload);
    if (_lastScreenRef.current === serialized) return;
    _lastScreenRef.current = serialized;
    registerScreen(view, payload.title, _screenData, payload.selectedCrop);
  }, [view, _pageTitles, _screenData, result, registerScreen]);



  // Check Web Speech API support
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SpeechRec) {
        setSpeechRecognitionSupported(false);
      }
    }
  }, []);

  const startVoiceInput = useCallback(() => {
    if (typeof window === "undefined") return;
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      setSpeechError(
        language === "te"
          ? "మీ బ్రౌజర్ వాయిస్ రికగ్నిషన్‌కు మద్దతు ఇవ్వదు. టెక్స్ట్ ద్వారా సందేశం పంపవచ్చు."
          : "Voice recognition is not supported in this browser. Please use text input."
      );
      return;
    }

    try {
      const recognition = new SpeechRec();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = language === "te" ? "te-IN" : "en-IN";

      recognition.onstart = () => {
        setIsListening(true);
        setSpeechError(null);
      };

      recognition.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((r: any) => r[0].transcript)
          .join("");
        setChatInput(transcript);
      };

      recognition.onerror = (event: any) => {
        setIsListening(false);
        if (event.error === "not-allowed") {
          setSpeechError(
            language === "te"
              ? "మైక్రోఫోన్ అనుమతి నిరాకరించబడింది. దయచేసి బ్రౌజర్‌లో మైక్రోఫోన్ అనుమతి ఇవ్వండి."
              : "Microphone permission denied. Please allow microphone access in your browser."
          );
        } else if (event.error === "no-speech") {
          setSpeechError(
            language === "te"
              ? "ధ్వని గుర్తించబడలేదు. దయచేసి మళ్ళీ స్పష్టంగా మాట్లాడండి."
              : "No speech detected. Please speak clearly into your microphone."
          );
        } else {
          setSpeechError(`Voice error: ${event.error}`);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.start();
    } catch (err: any) {
      setIsListening(false);
      setSpeechError(err.message || "Failed to start microphone.");
    }
  }, [language]);

  const speakText = useCallback(
    (textToSpeak: string) => {
      if (typeof window === "undefined" || !window.speechSynthesis) return;
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.lang = language === "te" ? "te-IN" : "en-IN";

      const voices = window.speechSynthesis.getVoices();
      const targetLang = language === "te" ? "te" : "en";
      const match = voices.find((v) => v.lang.startsWith(targetLang));
      if (match) utterance.voice = match;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      window.speechSynthesis.speak(utterance);
    },
    [language]
  );

  const stopSpeaking = useCallback(() => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  const handleClearChat = useCallback(() => {
    stopSpeaking();
    setChatMessages([
      {
        sender: "bot",
        text:
          language === "te"
            ? "నమస్కారం! నేను మీ క్షేత్రAI వ్యవసాయ సహాయకుడిని. మీ నేల, వాతావరణం, పంట సిఫార్సులు, ఎరువుల నిర్వహణ గురించి నన్ను అడగండి."
            : "Namaste! I am your KshetraIQ Agronomic Assistant. Ask me about crop recommendations, soil health, irrigation advice, or fertilizer management for your farm.",
      },
    ]);
  }, [language, stopSpeaking]);

  async function handlePredictYield() {
    setYieldLoading(true);
    setYieldError("");
    try {
      const res = await fetch(`${apiUrl}/api/v1/predictions/crop-yield`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          crop: yieldCrop,
          season: season || "Kharif",
          state: state || "Andhra Pradesh",
          crop_year: 2024,
          area_hectares: Math.max(0.1, Number(acreage || 1) * 0.404686),
          annual_rainfall_mm: Number(rainfall || (dashWeather?.rainfall ?? 900)),
          fertilizer_kg: Number(nitrogen || 90) + Number(phosphorus || 40) + Number(potassium || 40),
          pesticide_kg: 2.5,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setYieldResult(data);
    } catch (e: any) {
      setYieldError(e.message || "Failed to predict yield");
    } finally {
      setYieldLoading(false);
    }
  }

  async function handlePredictClimate() {
    setClimateLoading(true);
    setClimateError("");
    try {
      const res = await fetch(`${apiUrl}/api/v1/predictions/climate-scenario`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          crop: yieldCrop || "Rice",
          crop_year: 2024,
          season: season || "Kharif",
          state: state || "Andhra Pradesh",
          baseline_rainfall_mm: Number(rainfall || (dashWeather?.rainfall ?? 900)),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setClimateResult(data);
    } catch (e: any) {
      setClimateError(e.message || "Failed to simulate climate scenario");
    } finally {
      setClimateLoading(false);
    }
  }

  async function handleCalculateSustainability() {
    setSustainabilityLoading(true);
    setSustainabilityError("");
    try {
      const res = await fetch(`${apiUrl}/api/v1/predictions/sustainability`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          area_hectares: Math.max(0.1, Number(acreage || 1) * 0.404686),
          fertilizer_kg: Number(nitrogen || 90) + Number(phosphorus || 40) + Number(potassium || 40),
          pesticide_kg: 2.5,
          yield_tonnes_per_ha: yieldResult?.predicted_yield_tonnes_per_hectare || 3.8,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setSustainabilityResult(data);
    } catch (e: any) {
      setSustainabilityError(e.message || "Failed to calculate sustainability score");
    } finally {
      setSustainabilityLoading(false);
    }
  }

  async function handlePredictWeatherRisk() {
    setWeatherRiskLoading(true);
    setWeatherRiskError("");
    const activeToken = authToken || globalToken;
    try {
      const res = await fetch(`${apiUrl}/api/v1/predictions/weather-risk`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(activeToken ? { Authorization: `Bearer ${activeToken}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({
          month: 7,
          season: season || "Kharif",
          state: state || "Telangana",
          district: district || "Sangareddy",
          avg_temp_c: Number(dashWeather?.temp ?? temp ?? 28.7),
          wind_speed_kmh: 14.0,
          air_pressure_hpa: 1010.0,
          rainfall_mm: Number(dashWeather?.rainfall ?? rainfall ?? 692.7),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Error ${res.status}`);
      }
      const data = await res.json();
      setWeatherRiskResult(data);
    } catch (e: any) {
      setWeatherRiskError(e.message || "Failed to evaluate weather risk");
    } finally {
      setWeatherRiskLoading(false);
    }
  }

  // ──── Auth Handlers ────
  async function handleAuthSubmit() {
    setAuthLoading(true);
    setAuthError("");
    try {
      const endpoint = authTab === "register"
        ? `${apiUrl}/api/v1/auth/register`
        : `${apiUrl}/api/v1/auth/login`;
      const body: any = { email: authEmail, password: authPassword };
      if (authTab === "register" && authDisplayName.trim()) {
        body.display_name = authDisplayName.trim();
      }
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      if (handleAuthSuccess) {
        handleAuthSuccess(data, false);
      }
      setAuthToken(data.token);
      setAuthUser({
        user_id: data.user_id,
        email: data.email,
        display_name: data.display_name,
        created_at: data.created_at || new Date().toISOString(),
      });
      setShowAuthModal(false);
      setAuthEmail("");
      setAuthPassword("");
      setAuthDisplayName("");
    } catch (e: any) {
      setAuthError(e.message || "Authentication failed");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleLogout() {
    try {
      await globalLogout();
    } catch { /* ignore */ }
    setAuthToken(null);
    setAuthUser(null);
    router.push("/");
  }

  // ──── Market Price Handler ────
  async function handleMarketForecast() {
    setMktLoading(true);
    setMktError("");
    setMktResult(null);
    try {
      const mandiMetadata =
        marketMandiOptions.find((item) => item.name.toLowerCase() === mktMandi.toLowerCase()) ||
        (marketCatalog?.popular_mandis || DEFAULT_POPULAR_MANDIS).find((item) => item.name.toLowerCase() === mktMandi.toLowerCase()) ||
        (marketCatalog?.verified_pairs || []).find((item: any) => item.mandi?.toLowerCase() === mktMandi.toLowerCase());
      const res = await fetch(`${apiUrl}/api/v1/predictions/market-price`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({
          commodity: mktCommodity,
          mandi: mktMandi,
          state: mandiMetadata?.state,
          district: mandiMetadata?.district,
          days_ahead: Number(mktDaysAhead) || 7,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setMktResult(data);
    } catch (e: any) {
      setMktError(e.message || "Market price forecast failed");
    } finally {
      setMktLoading(false);
    }
  }

  // ──── Plant Disease Handler ────
  function handleDiseaseFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setDiseaseFile(file);
      setDiseaseResult(null);
      setDiseaseError("");
      const reader = new FileReader();
      reader.onload = (ev) => {
        setDiseasePreviewUrl(ev.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  }

  async function handleDiseaseScreening() {
    if (!diseaseFile) return;
    setDiseaseLoading(true);
    setDiseaseError("");
    setDiseaseResult(null);
    setPlantAnalysis(null);
    try {
      const formData = new FormData();
      formData.append("file", diseaseFile);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000);
      const res = await fetch(`${apiUrl}/api/plant-intelligence/analyze`, {
        method: "POST",
        headers: {
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        credentials: "include",
        body: formData,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setPlantAnalysis(data);
      const classifier = data?.executed_models?.disease_classifier;
      if (classifier?.result) setDiseaseResult(classifier.result);
      if (classifier?.error) setDiseaseError(classifier.error);

      // Register screen with latest plant analysis data
      registerScreen("disease", "Plant Disease & Intelligence", {
        analysis_id: data.analysis_id,
        disease: classifier?.result?.predicted_class,
        confidence: classifier?.result?.confidence_pct,
        caption: data?.executed_models?.blip?.result?.caption,
      });

      // Poll for background model completion (SAM, LIME, BLIP run in background threads)
      const analysisId = data.analysis_id;
      const pollInterval = setInterval(async () => {
        try {
          const pollRes = await fetch(`${apiUrl}/api/plant-intelligence/${analysisId}`, {
            headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
            credentials: "include",
          });
          if (!pollRes.ok) { clearInterval(pollInterval); return; }
          const pollData = await pollRes.json();
          setPlantAnalysis(pollData);
          const models = pollData?.executed_models || {};
          const allDone = ["sam", "lime", "blip"].every(
            (m) => models[m]?.status === "COMPLETED" || models[m]?.status === "FAILED"
          );
          if (allDone) {
            clearInterval(pollInterval);
            setDiseaseLoading(false);
          }
        } catch {
          clearInterval(pollInterval);
          setDiseaseLoading(false);
        }
      }, 4000); // poll every 4 seconds

      // Safety: stop polling after 10 minutes
      setTimeout(() => { clearInterval(pollInterval); setDiseaseLoading(false); }, 600000);
    } catch (e: any) {
      setDiseaseError(e?.name === "AbortError" ? "Complete plant analysis timed out. The saved analysis can be retried from this image." : (e.message || "Disease screening failed"));
      setDiseaseLoading(false);
    }
  }

  async function handleRunSingleModel(aid: string, model: string) {
    if (!aid || diseaseLoading) return;
    setDiseaseLoading(true);
    setDiseaseError("");
    try {
      const res = await fetch(`${apiUrl}/api/plant-intelligence/${aid}/${model}`, {
        method: "POST",
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        credentials: "include",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `Failed to run ${model.toUpperCase()}`);
      }
      const updated = await res.json();
      setPlantAnalysis(updated);
    } catch (e: any) {
      setDiseaseError(e.message || `Failed to execute ${model.toUpperCase()}`);
    } finally {
      setDiseaseLoading(false);
    }
  }

  async function handleRunMissingModels(aid: string) {
    if (!aid || diseaseLoading) return;
    setDiseaseLoading(true);
    setDiseaseError("");
    try {
      const pending = ["sam", "lime", "blip"];
      for (const m of pending) {
        try {
          await fetch(`${apiUrl}/api/plant-intelligence/${aid}/${m}`, {
            method: "POST",
            headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
            credentials: "include",
          });
        } catch (err) {
          console.error(`Error running model ${m}:`, err);
        }
      }
      const res = await fetch(`${apiUrl}/api/plant-intelligence/${aid}`, {
        headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
        credentials: "include",
      });
      if (res.ok) {
        const updated = await res.json();
        setPlantAnalysis(updated);
      }
    } catch (e: any) {
      setDiseaseError(e.message || "Failed to complete missing models.");
    } finally {
      setDiseaseLoading(false);
    }
  }

  // ──── Irrigation Calculator Handler ────
  async function handleIrrigationCalc() {
    setIrrLoading(true);
    setIrrError("");
    setIrrResult(null);
    try {
      const res = await fetch(`${apiUrl}/api/v1/predictions/irrigation`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({
          crop: irrCrop,
          crop_days: Number(irrCropDays) || 45,
          soil_moisture: Number(irrSoilMoisture) || 320,
          soil_type: irrSoilType,
          temperature: Number(irrTemp) || 28,
          rainfall_forecast_mm: Number(irrRainfallForecast) || 0,
          area_acres: Number(irrAreaAcres) || 2.5,
          soil_temperature: irrSoilTemp ? Number(irrSoilTemp) : undefined,
          humidity: irrHumidity ? Number(irrHumidity) : undefined,
          is_sensor_data: Boolean(irrSoilTemp && irrHumidity),
          force_deterministic: irrForceDeterministic,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setIrrResult(data);
    } catch (e: any) {
      setIrrError(e.message || "Irrigation calculation failed");
    } finally {
      setIrrLoading(false);
    }
  }

  // ──── Soil Health Score Handler ────
  async function handleCalculateSoilScore() {
    setCalculatingSoilScore(true);
    setSoilScoreError("");
    try {
      const payload: any = {};
      if (nitrogen) payload.nitrogen = parseFloat(nitrogen);
      if (phosphorus) payload.phosphorus = parseFloat(phosphorus);
      if (potassium) payload.potassium = parseFloat(potassium);
      if (ph) payload.ph = parseFloat(ph);

      const res = await fetch(`${apiUrl}/api/v1/soil/health-score`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setSoilScoreResult(data);
    } catch (e: any) {
      setSoilScoreError(e.message || "Soil health calculation failed");
    } finally {
      setCalculatingSoilScore(false);
    }
  }


  useEffect(() => {
    setApiUrl(getApiBaseUrl());
  }, []);

  const initialFetchDone = useRef(false);
  // Fetch initial data & backend runtime health
  useEffect(() => {
    if (!apiUrl || initialFetchDone.current) return;
    initialFetchDone.current = true;
    fetch(`${apiUrl}/health`)
      .then((r) => (r.ok ? r.json() : null))
      .then((h) => {
        if (h?.storage_mode) setStorageMode(h.storage_mode);
        if (h?.llm_configured !== undefined) setLlmConfigured(h.llm_configured === "true" || h.llm_configured === true);
        if (h?.llm_provider) setLlmProviderName(h.llm_provider);
      })
      .catch(() => {});

    refreshModelCatalog().catch(() => {});
    fetchAssessments();
    fetchUploads();
    fetchFarmProfile();
    fetchMarketCatalog();
  }, [apiUrl, fetchAssessments, fetchUploads, fetchFarmProfile, refreshModelCatalog, fetchMarketCatalog]);

  // Fetch dashboard weather when arriving at dashboard with a district set
  const fetchDashWeather = useCallback(() => {
    if (!apiUrl || !district || !state) return;
    fetch(
      `${apiUrl}/api/v1/weather/lookup?district=${encodeURIComponent(district)}&state=${encodeURIComponent(state)}&season=${encodeURIComponent(season)}`
    )
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data?.status === "available") {
          setDashWeather({
            temp: data.temperature_c,
            humidity: data.humidity_percent,
            rainfall: data.rainfall_mm,
            source: "Open-Meteo",
            district,
          });
        }
      })
      .catch(() => {});
  }, [apiUrl, district, state, season]);

  useEffect(() => {
    if (view === "dashboard") fetchDashWeather();
  }, [view, fetchDashWeather]);

  /* ── weather fetch for assessment form ── */
  async function handleWeatherFetch() {
    if (!district || !state) {
      setWeatherNotice(
        language === "te"
          ? "దయచేసి మొదట జిల్లా మరియు రాష్ట్రాన్ని నమోదు చేయండి."
          : "Please specify District and State first (Step 1)."
      );
      return;
    }
    setFetchingWeather(true);
    setWeatherNotice("");
    try {
      const res = await fetch(
        `${apiUrl}/api/v1/weather/lookup?district=${encodeURIComponent(district)}&state=${encodeURIComponent(state)}&season=${encodeURIComponent(season)}`
      );
      if (!res.ok) throw new Error(`Weather service returned HTTP ${res.status}`);
      const data = await res.json();
      if (data.status === "available") {
        setTemp(String(data.temperature_c));
        setHumidity(String(data.humidity_percent));
        setRainfall(String(data.rainfall_mm));
        setWeatherSourcePill("Open-Meteo Live");
        // Also update dashWeather so the weather tab shows the fetched data
        setDashWeather({
          temp: data.temperature_c,
          humidity: data.humidity_percent,
          rainfall: data.rainfall_mm,
          source: data.source?.includes("cached") ? "Open-Meteo (cached)" : "Open-Meteo Live",
          district,
        });
        setWeatherNotice(
          language === "te"
            ? `ప్రత్యక్ష వాతావరణం పొందబడింది (${district}, ${state})`
            : `Live observations retrieved for ${district}, ${state} via Open-Meteo.`
        );
      } else {
        const hint = data.hint || (data.source === "rate_limited"
          ? "Open-Meteo free tier limit reached. Please wait a few minutes and try again, or enter values manually."
          : "Live data unavailable for this location. You may enter values manually.");
        setWeatherNotice(
          language === "te"
            ? "ఈ ప్రాంతానికి ప్రత్యక్ష సమాచారం లభించలేదు. మాన్యువల్‌గా నమోదు చేయవచ్చు."
            : hint
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Network error";
      setWeatherNotice(
        language === "te"
          ? `వాతావరణ సర్వర్ సంప్రదింపు విఫలమైంది (${msg}).`
          : `Unable to reach weather provider (${msg}). Enter values manually.`
      );
    } finally {
      setFetchingWeather(false);
    }
  }

  /* ── submit assessment ── */
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    setResult(null);

    const num = (val: string) => {
      const trimmed = val.trim();
      return trimmed !== "" ? Number(trimmed) : null;
    };

    const prevCropsList = prevCrops
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    const payload = {
      farm_name: farmName.trim(),
      district: district.trim(),
      state: state.trim(),
      acreage: Number(acreage),
      irrigation_type: irrigation.trim(),
      water_availability: water.trim(),
      season: season.trim(),
      language,
      previous_crops: prevCropsList,
      planting_preferences: preferences.trim() || null,
      soil: {
        nitrogen_kg_ha: num(nitrogen),
        phosphorus_kg_ha: num(phosphorus),
        potassium_kg_ha: num(potassium),
        ph: num(ph),
      },
      weather:
        num(temp) !== null || num(humidity) !== null || num(rainfall) !== null
          ? {
              temperature_c: num(temp),
              humidity_percent: num(humidity),
              rainfall_mm: num(rainfall),
            }
          : null,
    };

    const requiredFields: Array<[string, string]> = [
      ["farm name", payload.farm_name],
      ["district", payload.district],
      ["state", payload.state],
      ["irrigation type", payload.irrigation_type],
      ["water availability", payload.water_availability],
      ["season", payload.season],
    ];
    const missingField = requiredFields.find(([, value]) => value.length < 2);
    if (missingField) {
      setError(`Please provide a valid ${missingField[0]} before running the assessment.`);
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(`${apiUrl}/api/v1/assessments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(globalToken ? { Authorization: `Bearer ${globalToken}` } : {}),
        },
        body: JSON.stringify(payload),
        credentials: "include",
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => null);
        if (errJson?.error?.details && Array.isArray(errJson.error.details)) {
          const detailMsgs = errJson.error.details
            .map((d: { loc?: string[]; msg?: string }) => {
              const field = d.loc?.slice(1)?.join(".") || "field";
              return `${field}: ${d.msg}`;
            })
            .join("; ");
          throw new Error(`Validation failed: ${detailMsgs}`);
        }
        const msg =
          errJson?.error?.message ||
          errJson?.detail ||
          `HTTP ${response.status} from API`;
        throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
      }

      const resData: Assessment = await response.json();
      setResult(resData);
      fetchAssessments();
      setView("results");
    } catch (err) {
      if (
        err instanceof TypeError &&
        err.message.toLowerCase().includes("failed to fetch")
      ) {
        setError(
          language === "te"
            ? `బ్యాకెండ్ API (${apiUrl}) కి కనెక్ట్ కాలేదు. FastAPI సర్వర్ పోర్ట్ 8000 లో నడుస్తున్నదో లేదో సరిచూసుకోండి.`
            : `Unable to connect to KshetraIQ API at ${apiUrl}. Please confirm the FastAPI backend is running.`
        );
      } else {
        setError(
          err instanceof Error ? err.message : "Unable to complete the assessment."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  /* ── report flow ── */
  function openReportConfirmation() {
    if (!result) return;
    setPdfError("");

    // Synchronously construct verified ReportPreview directly from result so modal ALWAYS opens in 0ms
    const cropModel = result.results?.find((r) => r.model_id === "crop-recommendation-v1");
    const pred = cropModel?.prediction;
    setReportPreview({
      assessment_id: result.assessment_id,
      farm_name: result.input.farm_name,
      location: `${result.input.district}, ${result.input.state}`,
      acreage: result.input.acreage,
      season: result.input.season,
      soil: {
        "N (kg/ha)": result.input.soil.nitrogen_kg_ha,
        "P (kg/ha)": result.input.soil.phosphorus_kg_ha,
        "K (kg/ha)": result.input.soil.potassium_kg_ha,
        "pH": result.input.soil.ph,
      },
      weather: {
        "Temperature (°C)": result.input.weather?.temperature_c ?? null,
        "Humidity (%)": result.input.weather?.humidity_percent ?? null,
        "Rainfall (mm)": result.input.weather?.rainfall_mm ?? null,
      },
      recommended_crop: (pred?.recommended_crop || "Needs Verified Inputs").toUpperCase(),
      confidence: pred?.confidence ? Math.round(pred.confidence * 100) : undefined,
      confirmation_prompt: (
        `Confirm generating the formal PDF report for ${result.input.farm_name}? ` +
        "This will compile verified soil analysis, weather observations, and model predictions."
      ),
      confirmation_prompt_te: (
        `${result.input.farm_name} కొరకు అధికారిక PDF నివేదికను రూపొందించడానికి నిర్ధారించాలా? ` +
        "ఇది నేల విశ్లేషణ, వాతావరణం మరియు AI సిఫార్సులతో నివేదికను తయారుచేస్తుంది."
      ),
      disclaimer: "The generated PDF includes traceable model versions and explicit agronomic assumptions.",
    });
    setShowReportModal(true);

    // In parallel, sync with backend preview if available
    const activeToken = authToken || globalToken;
    fetch(
      `${apiUrl}/api/v1/assessments/${result.assessment_id}/report/preview`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(activeToken ? { Authorization: `Bearer ${activeToken}` } : {}),
        },
        body: JSON.stringify(result),
        credentials: "include",
      }
    )
      .then((res) => (res.ok ? res.json() : null))
      .then((previewData) => {
        if (previewData) setReportPreview(previewData);
      })
      .catch(() => {});
  }

  async function confirmAndDownloadPdf() {
    if (!result) return;
    setGeneratingPdf(true);
    setPdfError("");
    const activeToken = authToken || globalToken;
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 25000);
      const res = await fetch(
        `${apiUrl}/api/v1/assessments/${result.assessment_id}/report/confirm`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(activeToken ? { Authorization: `Bearer ${activeToken}` } : {}),
          },
          body: JSON.stringify(result),
          credentials: "include",
          signal: controller.signal,
        }
      );
      clearTimeout(timeoutId);
      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || `PDF generation failed on server (HTTP ${res.status}).`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `KshetraIQ_Report_${result.assessment_id.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setShowReportModal(false);
    } catch (err: any) {
      setPdfError(err?.name === "AbortError" ? "PDF generation timed out. Please retry." : (err instanceof Error ? err.message : "PDF export failed."));
    } finally {
      setGeneratingPdf(false);
    }
  }

  const cropModel = result?.results.find((r) => r.model_id === "crop-recommendation-v1");
  const prediction = cropModel?.prediction;

  /* ── page title map ── */
  const pageTitles: Record<View, string> = {
    dashboard: t.navDashboard,
    profile: t.navProfile,
    assessment: t.navAssessment,
    recommendations: t.navCropRec,
    results: t.navCropRec,
    weather: t.navWeather,
    soil: t.navSoil,
    irrigation: t.navIrrigation,
    market: t.navMarket,
    disease: t.navDisease,
    reports: t.navReports,
    registry: t.navModelRegistry,
    settings: t.navSettings,
  };

  /* ══════════════════════════════════════════════════════════
     SIDEBAR
  ══════════════════════════════════════════════════════════ */
  function Sidebar() {
    const navItem = (
      icon: React.ReactNode,
      label: string,
      targetView: View,
      badge?: string
    ) => (
      <button
        key={label}
        className={`nav-item ${view === targetView ? "active" : ""}`}
        onClick={() => {
          setView(targetView);
          setSidebarOpen(false);
        }}
        aria-current={view === targetView ? "page" : undefined}
      >
        <span className="nav-icon">{icon}</span>
        <span className="nav-item-label">{label}</span>
        {badge && <span className="nav-badge">{badge}</span>}
      </button>
    );
    const intelligenceLink = (icon: React.ReactNode, label: string, href: string) => (
      <button key={href} className="nav-item" onClick={() => { router.push(href); setSidebarOpen(false); }}>
        <span className="nav-icon">{icon}</span><span className="nav-item-label">{label}</span><span className="nav-badge">New</span>
      </button>
    );

    return (
      <>
        <div
          className={`sidebar-overlay ${sidebarOpen ? "open" : ""}`}
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
        <aside className={`sidebar ${sidebarOpen ? "open" : ""}`} aria-label="Navigation">
          {/* Brand */}
          <div className="sidebar-brand" style={{ cursor: "pointer" }} onClick={() => router.push("/")} title="Return to Public Home">
            <div className="brand-crest" aria-hidden="true">
              <LeafIcon size={18} />
            </div>
            <div className="brand-text">
              <span className="brand-name">
                Kshetra<span className="brand-accent">IQ</span>
              </span>
              <span className="brand-tagline">
                {language === "te" ? "వ్యవసాయ AI మేధస్సు" : "Agri Intelligence"}
              </span>
            </div>
          </div>

          {/* Navigation (12 Modules) */}
          <nav className="sidebar-nav">
            <div className="nav-group">
              <span className="nav-group-label">
                {language === "te" ? "ప్రధాన విభాగాలు" : "Main Operations"}
              </span>
              {navItem(<LeafIcon size={15} />, t.navDashboard, "dashboard")}
              {navItem(<UserIcon size={15} />, t.navProfile, "profile")}
              {navItem(
                <FlaskIcon size={15} />,
                t.navAssessment,
                "assessment",
                result ? "1" : undefined
              )}
            </div>

            <div className="nav-group">
              <span className="nav-group-label">
                {language === "te" ? "వ్యవసాయ మేధస్సు" : "Agronomic Intelligence"}
              </span>
              {navItem(<BarChartIcon size={15} />, t.navCropRec, "recommendations", prediction ? "Ready" : undefined)}
              {navItem(<CloudSunIcon size={15} />, t.navWeather, "weather", dashWeather ? "Live" : undefined)}
              {navItem(<FlaskIcon size={15} />, t.navSoil, "soil")}
              {navItem(<DropletIcon size={15} />, t.navIrrigation, "irrigation")}
            </div>

            <div className="nav-group">
              <span className="nav-group-label">
                {language === "te" ? "విశ్లేషణ మోడల్స్" : "AI Modules"}
              </span>
              {navItem(<TrendingUpIcon size={15} />, t.navMarket, "market", "Live")}
              {navItem(
                <BugIcon size={15} />,
                language === "te" ? "మొక్కల వ్యాధులు & AI ఇంటెలిజెన్స్" : "Plant Disease & Intelligence",
                "disease",
                "Live"
              )}
              <a
                key="satellite-intelligence-external"
                href={SATELLITE_NDVI_APP_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="nav-item"
                onClick={() => setSidebarOpen(false)}
                style={{ textDecoration: "none" }}
              >
                <span className="nav-icon"><MapPinIcon size={15} /></span>
                <span className="nav-item-label">
                  {language === "te" ? "శాటిలైట్ ఇంటెలిజెన్స్ (NDVI)" : "Satellite Intelligence (NDVI)"}
                </span>
                <span className="nav-badge" style={{ background: "#2563eb", color: "#ffffff" }}>External ↗</span>
              </a>
            </div>

            <div className="nav-group">
              <span className="nav-group-label">
                {language === "te" ? "రికార్డులు & సిస్టమ్" : "System & Records"}
              </span>
              {navItem(<FileTextIcon size={15} />, t.navReports, "reports", result ? "Ready" : undefined)}
              {navItem(<DatabaseIcon size={15} />, t.navModelRegistry, "registry", "8")}
              {navItem(<SettingsIcon size={15} />, t.navSettings, "settings")}
            </div>
          </nav>

          {/* Footer */}
          <div className="sidebar-footer">
            <div className="sidebar-footer-item">
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "var(--green-600)",
                  display: "inline-block",
                }}
              />
              <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                API v0.4.0
              </span>
            </div>
          </div>
        </aside>
      </>
    );
  }

  /* ══════════════════════════════════════════════════════════
     TOPBAR
  ══════════════════════════════════════════════════════════ */
  function Topbar() {
    return (
      <header className="topbar">
        <div className="topbar-left">
          <button
            className="hamburger-btn"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle navigation"
          >
            <MenuIcon size={20} />
          </button>
          <div className="page-breadcrumb">
            <span>KshetraIQ</span>
            <span className="breadcrumb-sep">›</span>
            <span className="page-title">{pageTitles[view]}</span>
          </div>
        </div>
        <div className="topbar-right">
          <div className="api-status-chip" title={`API: ${apiUrl}`}>
            <span className="status-dot" />
            <span>API Live</span>
          </div>
          <button
            className="lang-btn"
            type="button"
            onClick={() => setLanguage(language === "en" ? "te" : "en")}
            aria-label="Toggle language"
          >
            <span className={language === "en" ? "lang-active" : ""}>EN</span>
            <span className="lang-sep">|</span>
            <span className={language === "te" ? "lang-active" : ""}>తెలుగు</span>
          </button>
          {authUser ? (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: "0.78rem", fontWeight: 500, color: "var(--green-800)" }}>
                {authUser.display_name || authUser.email.split("@")[0]}
              </span>
              <button
                className="btn-fetch"
                style={{ padding: "4px 10px", fontSize: "0.72rem" }}
                onClick={handleLogout}
              >
                {language === "te" ? "లాగ్‌అవుట్" : "Logout"}
              </button>
            </div>
          ) : (
            <button
              className="btn-fetch"
              style={{ padding: "4px 12px", fontSize: "0.78rem" }}
              onClick={() => setShowAuthModal(true)}
            >
              <UserIcon size={14} />
              <span>{language === "te" ? "లాగిన్" : "Sign In"}</span>
            </button>
          )}
        </div>
      </header>
    );
  }

  /* ══════════════════════════════════════════════════════════
     DASHBOARD VIEW
  ══════════════════════════════════════════════════════════ */
  function DashboardView() {
    const cropRes = result?.results.find((r) => r.model_id === "crop-recommendation-v1");
    const greetingName = globalUser?.full_name?.trim() || "Farmer";

    return (
      <div>
        {/* Welcome */}
        <div className="dashboard-welcome">
          <h1 className="welcome-greeting">
            {language === "te" ? `${getGreetingTe()}, ` : `${getGreeting()}, `}
            <span className="greeting-accent">{greetingName}</span>
          </h1>
          <p className="welcome-sub">{t.greetingSub}</p>
        </div>

        {/* 4 Summary Cards (Real Data or Honest Empty State) */}
        <div className="kpi-grid">
          {/* Card 1: Registered Land Area */}
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-icon-wrap green">
                <MapPinIcon size={18} />
              </div>
              <span className="kpi-status-badge verified">
                {acreage ? `${acreage} Ac` : "—"}
              </span>
            </div>
            <div className="kpi-value">{acreage ? `${acreage} Ac` : "—"}</div>
            <div className="kpi-label">{t.kpiLandArea}</div>
            <div className="kpi-sub">{farmName} · {district}</div>
          </div>

          {/* Card 2: Latest Assessment */}
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-icon-wrap green">
                <FlaskIcon size={18} />
              </div>
              <span className={`kpi-status-badge ${result ? "verified" : "pending"}`}>
                {result ? "Active" : "0"}
              </span>
            </div>
            <div className="kpi-value small">{result ? "Completed" : "Not Started"}</div>
            <div className="kpi-label">{t.kpiLatestAssessment}</div>
            <div className="kpi-sub">
              {result
                ? `ID: ${result.assessment_id.slice(0, 8)}… · ${storageMode === "sqlite_local" ? "SQLite DB" : result.storage}`
                : (storageMode === "sqlite_local" ? "SQLite DB Active" : "In-memory session")}
            </div>
          </div>

          {/* Card 3: Current Weather */}
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-icon-wrap blue">
                <CloudSunIcon size={18} />
              </div>
              <span className={`kpi-status-badge ${dashWeather ? "live" : "pending"}`}>
                {dashWeather ? "Live" : "—"}
              </span>
            </div>
            <div className="kpi-value small">
              {dashWeather?.temp != null ? `${dashWeather.temp}°C` : "—"}
            </div>
            <div className="kpi-label">{t.kpiWeather}</div>
            <div className="kpi-sub">
              {dashWeather
                ? `${dashWeather.humidity}% Humidity · ${dashWeather.rainfall}mm Rain`
                : t.kpiWeatherSub}
            </div>
          </div>

          {/* Card 4: Recommended Crop Status */}
          <div className="kpi-card">
            <div className="kpi-top">
              <div className="kpi-icon-wrap green">
                <SparklesIcon size={18} />
              </div>
              <span className={`kpi-status-badge ${prediction ? "verified" : "pending"}`}>
                {prediction ? "Verified" : "Pending"}
              </span>
            </div>
            <div className="kpi-value small">
              {prediction
                ? (language === "te"
                    ? prediction.recommended_crop_te
                    : prediction.recommended_crop.toUpperCase())
                : "—"}
            </div>
            <div className="kpi-label">{t.kpiCropStatus}</div>
            <div className="kpi-sub">
              {prediction
                ? `${Math.round(prediction.confidence * 100)}% Model Confidence`
                : (language === "te" ? "అంచనా అవసరం" : "Assessment pending")}
            </div>
          </div>
        </div>

        {/* Main grid */}
        <div className="dashboard-grid">
          {/* LEFT column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Soil Health */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  <span className="card-title-icon">
                    <FlaskIcon size={16} />
                  </span>
                  {t.dashSoilCard}
                </span>
                {!result && (
                  <button
                    className="card-action-btn"
                    onClick={() => { setView("assessment"); setActiveStep(2); }}
                  >
                    {language === "te" ? "నేల నమోదు చేయండి" : "Add Soil Data"}
                  </button>
                )}
              </div>
              <div className="card-body">
                {result ? (
                  <>
                    <div className="soil-npk-row">
                      {[
                        { sym: "N", val: nitrogen, unit: "kg/ha", cls: "n" },
                        { sym: "P", val: phosphorus, unit: "kg/ha", cls: "p" },
                        { sym: "K", val: potassium, unit: "kg/ha", cls: "k" },
                        { sym: "pH", val: ph, unit: "0–14", cls: "ph" },
                      ].map((item) => (
                        <div key={item.sym} className={`nutrient-pill ${item.cls}`}>
                          <span className="nutrient-pill-symbol">{item.sym}</span>
                          <span className="nutrient-pill-value">{item.val}</span>
                          <span className="nutrient-pill-unit">{item.unit}</span>
                        </div>
                      ))}
                    </div>
                    <div className="soil-status-row">
                      <span className="soil-status-label">
                        {language === "te" ? "పొలం:" : "Farm:"} {farmName}
                      </span>
                      <span className="soil-status-value">
                        {district}, {state}
                      </span>
                    </div>
                    {result.advisor?.soil_health_assessment?.score != null && (
                      <div style={{ marginTop: 12, fontSize: "0.82rem", color: "var(--green-900)", fontWeight: 700 }}>
                        SOIL HEALTH SCORE: {Math.round(result.advisor.soil_health_assessment.score)} / 100 — {result.advisor.soil_health_assessment.category}
                        {result.advisor.soil_health_assessment.is_provisional ? " (provisional)" : ""}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="empty-state">
                    <div className="empty-icon-wrap">
                      <FlaskIcon size={26} />
                    </div>
                    <div className="empty-title">{t.noAssessmentYet}</div>
                    <div className="empty-desc">{t.noAssessmentDesc}</div>
                    <button
                      className="card-action-btn"
                      style={{ marginTop: 4 }}
                      onClick={() => setView("assessment")}
                    >
                      {t.runAssessmentBtn}
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Assessments Table */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  <span className="card-title-icon">
                    <FileTextIcon size={16} />
                  </span>
                  {t.dashHistoryCard}
                </span>
              </div>
              {savedAssessments.length > 0 ? (
                <div style={{ overflowX: "auto" }}>
                  <table className="assessment-table">
                    <thead>
                      <tr>
                        <th>{language === "te" ? "ఐడి" : "Assessment ID"}</th>
                        <th>{language === "te" ? "వాతావరణం" : "Weather"}</th>
                        <th>{language === "te" ? "పంట సిఫార్సు" : "Crop Rec."}</th>
                        <th>{language === "te" ? "నిల్వ విధానం" : "Storage"}</th>
                        <th>{language === "te" ? "చర్య" : "Action"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {savedAssessments.map((item) => {
                        const rec = item.results.find((r) => r.model_id === "crop-recommendation-v1");
                        const p = rec?.prediction;
                        return (
                          <tr key={item.assessment_id}>
                            <td style={{ fontFamily: "monospace", fontSize: "0.78rem" }}>
                              {item.assessment_id.slice(0, 8)}…
                            </td>
                            <td className="table-cell-muted">
                              <span className="source-tag">{item.weather_source}</span>
                            </td>
                            <td>
                              {p ? (
                                <span className="crop-pill">
                                  {language === "te" ? p.recommended_crop_te : p.recommended_crop.toUpperCase()}
                                </span>
                              ) : (
                                <span className="table-cell-muted">—</span>
                              )}
                            </td>
                            <td>
                              <span className="source-tag">{item.storage}</span>
                            </td>
                            <td>
                              <button
                                type="button"
                                className="view-btn"
                                onClick={() => {
                                  setResult(item);
                                  setView("results");
                                }}
                              >
                                {language === "te" ? "చూడండి" : "View"}
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : result ? (
                <table className="assessment-table">
                  <thead>
                    <tr>
                      <th>{language === "te" ? "పొలం" : "Farm"}</th>
                      <th>{language === "te" ? "స్థానం" : "Location"}</th>
                      <th>{language === "te" ? "పంట సిఫార్సు" : "Crop Rec."}</th>
                      <th>{language === "te" ? "స్థితి" : "Status"}</th>
                      <th>{language === "te" ? "చర్య" : "Action"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>{farmName}</td>
                      <td className="table-cell-muted">{district}, {state}</td>
                      <td>
                        {prediction ? (
                          <span className="crop-pill">
                            {language === "te"
                              ? prediction.recommended_crop_te
                              : prediction.recommended_crop.toUpperCase()}
                          </span>
                        ) : (
                          <span className="table-cell-muted">—</span>
                        )}
                      </td>
                      <td>
                        <span className={`status-chip ${cropModel?.status || ""}`}>
                          {cropModel?.status || "—"}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="view-btn"
                          onClick={() => setView("results")}
                        >
                          {language === "te" ? "చూడండి" : "View"}
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              ) : (
                <div className="empty-state" style={{ paddingTop: 24, paddingBottom: 24 }}>
                  <div className="empty-title" style={{ fontSize: "0.82rem" }}>
                    {language === "te" ? "ఇంకా అంచనాలు లేవు" : "No assessments recorded yet"}
                  </div>
                  <div className="empty-desc">
                    {language === "te"
                      ? "అంచనా వేసిన తర్వాత ఇక్కడ చరిత్ర కనిపిస్తుంది."
                      : "Assessment history appears here. Assessments are stored in memory."}
                  </div>
                </div>
              )}
            </div>

            {/* Model Registry */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  <span className="card-title-icon">
                    <DatabaseIcon size={16} />
                  </span>
                  {t.dashModelsCard}
                </span>
              </div>
              <div className="registry-list">
                {modelCatalog.length > 0 ? (
                  modelCatalog.map((m) => (
                    <div key={m.model_id} className="registry-row">
                      <div
                        className={`registry-dot ${m.contract_status}`}
                        title={m.contract_status}
                      />
                      <span className="registry-model-name">{m.model_id}</span>
                      <span className="registry-model-note">{m.note.slice(0, 80)}…</span>
                    </div>
                  ))
                ) : (
                  <div className="empty-state" style={{ padding: "20px" }}>
                    <div className="empty-desc">
                      {language === "te"
                        ? "API కి కనెక్ట్ కాలేదు. బ్యాకెండ్ నడుస్తున్నదో సరిచూడండి."
                        : "Could not load model catalog. Ensure the backend is running."}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* RIGHT column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Weather Widget */}
            <div className="card" style={{ overflow: "hidden" }}>
              <div className="weather-widget">
                {dashWeather ? (
                  <>
                    <div className="weather-header-section">
                      <div className="weather-location">
                        <MapPinIcon size={12} />
                        {dashWeather.district}, {state}
                      </div>
                      <div className="weather-temp-row">
                        <span className="weather-temp-value">{dashWeather.temp}</span>
                        <span className="weather-temp-unit">°C</span>
                      </div>
                      <div className="weather-desc">
                        {language === "te" ? "ప్రస్తుత వాతావరణం" : "Current Conditions"}
                      </div>
                    </div>
                    <div className="weather-metrics">
                      <div className="weather-metric">
                        <span className="weather-metric-label">
                          {language === "te" ? "తేమ" : "Humidity"}
                        </span>
                        <span className="weather-metric-value">{dashWeather.humidity}%</span>
                      </div>
                      <div className="weather-metric">
                        <span className="weather-metric-label">
                          {language === "te" ? "వర్షపాతం" : "Seasonal Rain"}
                        </span>
                        <span className="weather-metric-value">{dashWeather.rainfall} mm</span>
                      </div>
                    </div>
                    <div className="weather-source-row">
                      <InfoIcon size={11} />
                      {language === "te" ? "వనరు:" : "Source:"} {dashWeather.source} · {language === "te" ? "సీజనల్ అంచనా" : "Seasonal estimate"}
                    </div>
                  </>
                ) : (
                  <>
                    <div
                      className="weather-header-section"
                      style={{
                        background:
                          "linear-gradient(135deg, var(--green-900) 0%, var(--green-700) 100%)",
                      }}
                    >
                      <div className="weather-location">
                        <MapPinIcon size={12} />
                        {district || "—"}, {state || "—"}
                      </div>
                      <div className="weather-temp-row">
                        <span className="weather-temp-value">—</span>
                        <span className="weather-temp-unit">°C</span>
                      </div>
                      <div className="weather-desc">
                        {language === "te" ? "లోడ్ అవుతోంది…" : "Loading weather…"}
                      </div>
                    </div>
                    <div className="weather-unavailable">
                      {language === "te"
                        ? "వాతావరణ డేటా అందుబాటులో లేదు. పొలం మొదట నమోదు చేయండి."
                        : "Weather data unavailable. Enter district & state in the assessment form first."}
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Suggested Next Steps */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  <span className="card-title-icon">
                    <CheckCircleIcon size={16} />
                  </span>
                  {t.dashTasksCard}
                </span>
              </div>
              <div className="task-list">
                {[
                  {
                    cls: "primary",
                    title: language === "te"
                      ? "నేల ల్యాబ్ అంచనా వేయండి"
                      : "Run a soil lab assessment",
                    desc: language === "te"
                      ? "N, P, K మరియు pH విలువలతో రాండమ్ ఫారెస్ట్ మోడల్ అమలు చేయండి"
                      : "Submit N, P, K and pH from your Soil Health Card",
                    action: () => setView("assessment"),
                  },
                  {
                    cls: "secondary",
                    title: language === "te"
                      ? "వాతావరణం ధృవీకరించండి"
                      : "Verify live weather data",
                    desc: language === "te"
                      ? "ఓపెన్-మెటియో ద్వారా మీ జిల్లా వాతావరణం పొందండి"
                      : "Fetch real-time district observations via Open-Meteo",
                    action: fetchDashWeather,
                  },
                  {
                    cls: "info",
                    title: language === "te"
                      ? "PDF నివేదిక తయారు చేయండి"
                      : "Generate PDF assessment report",
                    desc: language === "te"
                      ? "అంచనా తర్వాత అధికారిక నివేదికను డౌన్‌లోడ్ చేసుకోండి"
                      : "Two-step confirmed ReportLab export after assessment",
                    action: result ? openReportConfirmation : () => setView("assessment"),
                  },
                ].map((item, i) => (
                  <button
                    key={i}
                    className="task-item"
                    style={{
                      border: "none",
                      background: "none",
                      cursor: "pointer",
                      textAlign: "left",
                      width: "100%",
                    }}
                    onClick={item.action}
                  >
                    <span className={`task-indicator ${item.cls}`} />
                    <div className="task-content">
                      <div className="task-title">{item.title}</div>
                      <div className="task-desc">{item.desc}</div>
                    </div>
                    <ArrowRightIcon
                      size={14}
                      style={{ color: "var(--text-muted)", flexShrink: 0 }}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Storage notice */}
            <div className="storage-info-strip">
              <InfoIcon size={15} className="storage-icon" />
              <div>
                <strong>{language === "te" ? "నిల్వ స్థితి:" : "Storage:"}</strong>{" "}
                {storageMode === "sqlite_local"
                  ? (language === "te"
                      ? "SQLite లోకల్ డేటాబేస్ (శాశ్వతం) — సర్వర్ రీస్టార్ట్ అయినా మీ అసెస్‌మెంట్ రికార్డులు భద్రంగా ఉంటాయి."
                      : "SQLite Local Database (Persistent) — Farm assessments and reports are preserved across server restarts in .tmp/kshetraiq.db.")
                  : storageMode === "supabase"
                  ? (language === "te" ? "సుపాబేస్ క్లౌడ్ నిల్వ సక్రియం." : "Supabase Cloud Database connected.")
                  : (language === "te"
                      ? "ఇన్-మెమరీ మాత్రమే. సర్వర్ రీస్టార్ట్ అయితే అసెస్‌మెంట్లు తొలగించబడతాయి."
                      : "In-memory only. Supabase credentials not configured — assessments lost on restart.")}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════
     ASSESSMENT FORM VIEW
  ══════════════════════════════════════════════════════════ */
  function AssessmentView() {
    const steps = [
      { num: 1, label: language === "te" ? "పొలం" : "Farm", title: t.step1 },
      { num: 2, label: language === "te" ? "నేల" : "Soil", title: t.step2 },
      { num: 3, label: language === "te" ? "వాతావరణం" : "Weather", title: t.step3 },
      { num: 4, label: language === "te" ? "గమనికలు" : "Notes", title: t.step4 },
    ];

    return (
      <div className="assessment-page">
        <div className="assessment-page-header">
          <h1 className="page-heading">
            {language === "te" ? "సమగ్ర పొలం అంచనా" : "Farm Assessment Intake"}
          </h1>
          <p className="page-subheading">
            {language === "te"
              ? "నేల ల్యాబ్ విలువలు మరియు వాతావరణ డేటాతో ధృవీకరించబడిన పంట సిఫార్సులు పొందండి."
              : "Provide certified soil lab measurements and agro-meteorological data to receive verified crop recommendations."}
          </p>
        </div>

        {/* Step progress */}
        <div className="step-progress" role="tablist">
          {steps.map((s) => (
            <button
              key={s.num}
              role="tab"
              aria-selected={activeStep === s.num}
              className={`step-progress-item ${activeStep === s.num ? "active" : ""} ${activeStep > s.num ? "completed" : ""}`}
              onClick={() => setActiveStep(s.num)}
              type="button"
            >
              <div className="step-num">
                {activeStep > s.num ? (
                  <CheckCircleIcon size={14} />
                ) : (
                  s.num
                )}
              </div>
              <div>
                <span className="step-step-label">{s.label}</span>
                <span className="step-step-title">{s.title}</span>
              </div>
            </button>
          ))}
        </div>

        <form onSubmit={submit} noValidate>
          {/* ── STEP 1: Farm & Location ── */}
          <div className={activeStep === 1 ? "step-visible" : "step-hidden"}>
            <div className="form-card">
              <div className="form-card-header">
                <MapPinIcon size={18} className="form-card-icon" />
                <div>
                  <div className="form-card-title">{t.step1}</div>
                  <div className="form-card-subtitle">
                    {language === "te"
                      ? "పొలం స్థానం మరియు వ్యవసాయ వివరాలు"
                      : "Farm identity, location and agronomic context"}
                  </div>
                </div>
              </div>
              <div className="form-card-body">
                <div className="form-col-full">
                  <label className="field-label">
                    {t.farmNameLbl} <span className="field-req">*</span>
                    <input
                      type="text"
                      required
                      minLength={2}
                      maxLength={100}
                      value={farmName}
                      onChange={(e) => setFarmName(e.target.value)}
                      placeholder={language === "te" ? "రైతు క్షేత్రం" : "e.g., Rythu Farm"}
                      className="form-input"
                      id="inp-farm-name"
                    />
                  </label>
                </div>
                <div className="form-grid-3">
                  <label className="field-label">
                    {t.stateLbl} <span className="field-req">*</span>
                    <select
                      required
                      value={state}
                      onChange={(e) => selectState(e.target.value)}
                      className="form-select"
                      id="inp-state"
                    >
                      <option value="">Select a state</option>
                      {SUPPORTED_STATES.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label className="field-label">
                    {t.districtLbl} <span className="field-req">*</span>
                    <select
                      required
                      value={district}
                      disabled={!state}
                      onChange={(e) => setDistrict(e.target.value)}
                      className="form-select"
                      id="inp-district"
                    >
                      <option value="">{state ? "Select a district" : "Select state first"}</option>
                      {districtChoices.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label className="field-label">
                    {t.acreageLbl} <span className="field-req">*</span>
                    <input
                      type="number"
                      step="0.1"
                      min="0.1"
                      max="100000"
                      required
                      value={acreage}
                      onChange={(e) => setAcreage(e.target.value)}
                      className="form-input"
                      id="inp-acreage"
                    />
                  </label>
                </div>
                <div className="form-grid-3">
                  <label className="field-label">
                    {t.seasonLbl} <span className="field-req">*</span>
                    <select
                      value={season}
                      onChange={(e) => setSeason(e.target.value)}
                      className="form-select"
                      id="inp-season"
                    >
                      <option value="Kharif">Kharif (ఖరీఫ్ — Monsoon)</option>
                      <option value="Rabi">Rabi (రబీ — Winter)</option>
                      <option value="Summer">Summer / Zaid (ఎండకాలం)</option>
                    </select>
                  </label>
                  <label className="field-label">
                    {t.irrigationLbl} <span className="field-req">*</span>
                    <select
                      value={irrigation}
                      onChange={(e) => setIrrigation(e.target.value)}
                      className="form-select"
                      id="inp-irrigation"
                    >
                      <option value="Drip">Drip (డ్రిప్)</option>
                      <option value="Sprinkler">Sprinkler (స్ప్రింక్లర్)</option>
                      <option value="Canal">Canal (కాలువ)</option>
                      <option value="Rainfed">Rainfed (వర్షాధార)</option>
                      <option value="Flood">Flood Furrow (మురుగు)</option>
                    </select>
                  </label>
                  <label className="field-label">
                    {t.waterLbl} <span className="field-req">*</span>
                    <select
                      value={water}
                      onChange={(e) => setWater(e.target.value)}
                      className="form-select"
                      id="inp-water"
                    >
                      <option value="Borewell">Borewell (బోరుబావి)</option>
                      <option value="Canal supply">Canal Supply (కాలువ నీరు)</option>
                      <option value="Seasonal rainfall">Seasonal Rainfall (వర్షం)</option>
                      <option value="Farm Pond">Farm Pond (చెరువు)</option>
                    </select>
                  </label>
                </div>
                <div className="step-actions">
                  <div />
                  <button
                    type="button"
                    className="btn-next"
                    onClick={() => setActiveStep(2)}
                  >
                    <span>{language === "te" ? "నేల వివరాలకు వెళ్ళండి" : "Proceed to Soil Chemistry"}</span>
                    <ArrowRightIcon size={15} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ── STEP 2: Soil Chemistry ── */}
          <div className={activeStep === 2 ? "step-visible" : "step-hidden"}>
            <div className="form-card">
              <div className="form-card-header">
                <FlaskIcon size={18} className="form-card-icon" />
                <div>
                  <div className="form-card-title">{t.step2}</div>
                  <div className="form-card-subtitle">{t.soilCardSubtitle}</div>
                </div>
              </div>
              <div className="form-card-body">
                <div className="nutrient-cards-grid">
                  {[
                    {
                      sym: "N",
                      name: "Nitrogen",
                      range: "Normal: 100–250 kg/ha",
                      val: nitrogen,
                      set: setNitrogen,
                      min: 0,
                      max: 1000,
                      id: "inp-n",
                      lbl: t.nLbl,
                    },
                    {
                      sym: "P",
                      name: "Phosphorus",
                      range: "Normal: 30–80 kg/ha",
                      val: phosphorus,
                      set: setPhosphorus,
                      min: 0,
                      max: 1000,
                      id: "inp-p",
                      lbl: t.pLbl,
                    },
                    {
                      sym: "K",
                      name: "Potassium",
                      range: "Normal: 30–150 kg/ha",
                      val: potassium,
                      set: setPotassium,
                      min: 0,
                      max: 1000,
                      id: "inp-k",
                      lbl: t.kLbl,
                    },
                    {
                      sym: "pH",
                      name: "Soil Acidity",
                      range: "Ideal: 6.0 – 7.5",
                      val: ph,
                      set: setPh,
                      min: 0,
                      max: 14,
                      step: 0.1,
                      id: "inp-ph",
                      lbl: t.phLbl,
                    },
                  ].map((item) => (
                    <div key={item.sym} className="nutrient-input-card">
                      <span className="nutrient-card-symbol">{item.sym}</span>
                      <span className="nutrient-card-name">{item.name}</span>
                      <span className="nutrient-range">{item.range}</span>
                      <label htmlFor={item.id} style={{ display: "block" }}>
                        <span style={{ display: "none" }}>{item.lbl}</span>
                        <input
                          id={item.id}
                          type="number"
                          min={item.min}
                          max={item.max}
                          step={(item as { step?: number }).step || 1}
                          required
                          value={item.val}
                          onChange={(e) => item.set(e.target.value)}
                          className="nutrient-field-input"
                          aria-label={item.lbl}
                        />
                      </label>
                    </div>
                  ))}
                </div>
                <div
                  style={{
                    background: "var(--blue-bg)",
                    border: "1px solid #b8d9f5",
                    borderRadius: "var(--r-md)",
                    padding: "10px 14px",
                    fontSize: "0.75rem",
                    color: "var(--blue-text)",
                    display: "flex",
                    gap: 8,
                    alignItems: "flex-start",
                  }}
                >
                  <InfoIcon size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>
                    {language === "te"
                      ? "ఈ విలువలు సర్టిఫైడ్ నేల ల్యాబ్ నివేదిక నుండి తీసుకోవాలి. ఊహించబడిన విలువలు అనుమతించబడవు."
                      : "Values must come from a certified soil laboratory report or Soil Health Card. Do not estimate or photograph-infer these values."}
                  </span>
                </div>

                <div style={{ marginTop: 18 }}>
                  <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--green-950)", marginBottom: 4 }}>
                    {t.uploadSoilReportTitle}
                  </div>
                  <FileUploadBox
                    category="soil_report"
                    title={language === "te" ? "సాయిల్ ల్యాబ్ రిపోర్ట్ / సాయిల్ హెల్త్ కార్డు అప్‌లోడ్" : "Upload Soil Lab Report / Soil Health Card"}
                    subtitle={t.uploadHint}
                    accept=".pdf,.jpg,.jpeg,.png,.webp"
                    onUpload={handleFileUpload}
                    uploading={uploadingCategory === "soil_report"}
                    files={uploadedFiles}
                    onDelete={handleDeleteUpload}
                    language={language}
                  />
                  {uploadError && uploadingCategory === "soil_report" && (
                    <div style={{ color: "var(--red-text)", fontSize: "0.75rem", marginTop: 4 }}>
                      {uploadError}
                    </div>
                  )}
                  {uploadSuccessMsg && (
                    <div style={{ color: "var(--green-700)", fontSize: "0.75rem", marginTop: 4 }}>
                      {uploadSuccessMsg}
                    </div>
                  )}
                </div>

                <div className="step-actions">
                  <button type="button" className="btn-back" onClick={() => setActiveStep(1)}>
                    {t.backBtn}
                  </button>
                  <button type="button" className="btn-next" onClick={() => setActiveStep(3)}>
                    <span>{language === "te" ? "వాతావరణ వివరాలకు వెళ్ళండి" : "Proceed to Weather"}</span>
                    <ArrowRightIcon size={15} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ── STEP 3: Weather Context ── */}
          <div className={activeStep === 3 ? "step-visible" : "step-hidden"}>
            <div className="form-card">
              <div className="form-card-header">
                <CloudSunIcon size={18} className="form-card-icon" />
                <div>
                  <div className="form-card-title">{t.step3}</div>
                  <div className="form-card-subtitle">
                    {language === "te"
                      ? "ఓపెన్-మెటియో ద్వారా ప్రత్యక్ష వాతావరణం పొందండి లేదా మాన్యువల్‌గా నమోదు చేయండి."
                      : "Fetch live district observations via Open-Meteo or enter field station readings manually."}
                  </div>
                </div>
              </div>
              <div className="form-card-body">
                <div className="weather-fetch-strip">
                  <div>
                    <div className="weather-fetch-label">Open-Meteo Meteorological Gateway</div>
                    <div className="weather-fetch-sublabel">
                      {language === "te"
                        ? `${district}, ${state} కోసం ప్రత్యక్ష వాతావరణం తీసుకోండి`
                        : `Query live observations for ${district}, ${state}`}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn-fetch"
                    onClick={handleWeatherFetch}
                    disabled={fetchingWeather}
                    id="btn-fetch-weather"
                  >
                    <RefreshIcon size={14} className={fetchingWeather ? "spin" : ""} />
                    <span>{fetchingWeather ? t.fetchingBtn : t.fetchWeatherBtn}</span>
                  </button>
                </div>

                {weatherNotice && (
                  <div className="weather-notice-banner">
                    <InfoIcon size={14} style={{ flexShrink: 0 }} />
                    <span>{weatherNotice}</span>
                    {weatherSourcePill && (
                      <span className="weather-source-chip">{weatherSourcePill}</span>
                    )}
                  </div>
                )}

                <div className="form-grid-3">
                  <label className="field-label">
                    {t.tempLbl}
                    <span className="field-hint">
                      {language === "te" ? "ఐచ్ఛికం — సిస్టమ్ ద్వారా నింపవచ్చు" : "Optional — auto-filled via Open-Meteo"}
                    </span>
                    <input
                      type="number"
                      step="0.1"
                      min="-10"
                      max="60"
                      value={temp}
                      onChange={(e) => setTemp(e.target.value)}
                      placeholder="e.g., 28.5"
                      className="form-input"
                      id="inp-temp"
                    />
                  </label>
                  <label className="field-label">
                    {t.humidityLbl}
                    <span className="field-hint">
                      {language === "te" ? "ఐచ్ఛికం" : "Optional"}
                    </span>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="100"
                      value={humidity}
                      onChange={(e) => setHumidity(e.target.value)}
                      placeholder="e.g., 75"
                      className="form-input"
                      id="inp-humidity"
                    />
                  </label>
                  <label className="field-label">
                    {t.rainfallLbl}
                    <span className="field-hint">
                      {language === "te" ? "సీజనల్ అంచనా (mm)" : "Seasonal estimate (mm)"}
                    </span>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      max="5000"
                      value={rainfall}
                      onChange={(e) => setRainfall(e.target.value)}
                      placeholder="e.g., 650"
                      className="form-input"
                      id="inp-rainfall"
                    />
                  </label>
                </div>
                <div className="step-actions">
                  <button type="button" className="btn-back" onClick={() => setActiveStep(2)}>
                    {t.backBtn}
                  </button>
                  <button type="button" className="btn-next" onClick={() => setActiveStep(4)}>
                    <span>{language === "te" ? "గమనికలకు వెళ్ళండి" : "Proceed to Cropping Notes"}</span>
                    <ArrowRightIcon size={15} />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ── STEP 4: Cropping Notes & Submit ── */}
          <div className={activeStep === 4 ? "step-visible" : "step-hidden"}>
            <div className="form-card">
              <div className="form-card-header">
                <LeafIcon size={18} className="form-card-icon" />
                <div>
                  <div className="form-card-title">{t.step4}</div>
                  <div className="form-card-subtitle">
                    {language === "te"
                      ? "పంట చరిత్ర మరియు రైతు ప్రాధాన్యతలు"
                      : "Crop rotation history and farmer preferences for the rule-based advisor"}
                  </div>
                </div>
              </div>
              <div className="form-card-body">
                <div className="form-col-full">
                  <label className="field-label">
                    {t.prevCropsLbl}
                    <span className="field-hint">
                      {language === "te" ? "కామాలతో వేరు చేయండి" : "Comma-separated, e.g., Paddy, Cotton"}
                    </span>
                    <input
                      type="text"
                      value={prevCrops}
                      onChange={(e) => setPrevCrops(e.target.value)}
                      placeholder="Paddy, Cotton / వరి, పత్తి"
                      className="form-input"
                      id="inp-prev-crops"
                    />
                  </label>
                </div>
                <div className="form-col-full">
                  <label className="field-label">
                    {t.prefLbl}
                    <span className="field-hint">{language === "te" ? "ఐచ్ఛికం" : "Optional"}</span>
                    <textarea
                      rows={3}
                      value={preferences}
                      onChange={(e) => setPreferences(e.target.value)}
                      placeholder={
                        language === "te"
                          ? "e.g., తక్కువ రసాయనాలు, పప్పు సేద్యం ఆసక్తి"
                          : "e.g., Interested in pulse intercropping, low chemical usage"
                      }
                      className="form-textarea"
                      id="inp-preferences"
                    />
                  </label>
                </div>

                <div style={{ marginTop: 16 }}>
                  <div style={{ fontWeight: 600, fontSize: "0.85rem", color: "var(--green-950)", marginBottom: 4 }}>
                    {language === "te" ? "పొలం / పంట ఫోటోలు (ఐచ్ఛికం)" : "Field & Crop Photos (Optional)"}
                  </div>
                  <FileUploadBox
                    category="field_photo"
                    title={t.uploadFieldPhotoTitle}
                    subtitle={t.uploadHint}
                    accept=".jpg,.jpeg,.png,.webp"
                    onUpload={handleFileUpload}
                    uploading={uploadingCategory === "field_photo"}
                    files={uploadedFiles}
                    onDelete={handleDeleteUpload}
                    language={language}
                  />
                  {uploadError && uploadingCategory === "field_photo" && (
                    <div style={{ color: "var(--red-text)", fontSize: "0.75rem", marginTop: 4 }}>
                      {uploadError}
                    </div>
                  )}
                  {uploadSuccessMsg && (
                    <div style={{ color: "var(--green-700)", fontSize: "0.75rem", marginTop: 4 }}>
                      {uploadSuccessMsg}
                    </div>
                  )}
                </div>

                {/* Review summary */}
                <div className="review-summary">
                  <div className="review-summary-title">
                    {language === "te" ? "అంచనా సమీక్ష" : "Assessment Summary"}
                  </div>
                  <div className="review-pills">
                    {[
                      `${language === "te" ? "పొలం:" : "Farm:"} ${farmName}`,
                      `${district}, ${state}`,
                      `${acreage} ${language === "te" ? "ఎకరాలు" : "Acres"}`,
                      `pH: ${ph}`,
                      `N: ${nitrogen} | P: ${phosphorus} | K: ${potassium}`,
                      `${season}`,
                    ].map((pill) => (
                      <span key={pill} className="review-pill">{pill}</span>
                    ))}
                  </div>
                </div>

                <button
                  type="submit"
                  className="btn-submit-run"
                  disabled={loading}
                  aria-busy={loading}
                  id="btn-submit-assessment"
                >
                  {loading ? (
                    <>
                      <RefreshIcon size={19} className="spin" />
                      <span>{t.submittingBtn}</span>
                    </>
                  ) : (
                    <>
                      <SparklesIcon size={19} />
                      <span>{t.submitBtn}</span>
                    </>
                  )}
                </button>

                <div className="step-actions" style={{ marginTop: 12 }}>
                  <button type="button" className="btn-back" onClick={() => setActiveStep(3)}>
                    {t.backBtn}
                  </button>
                </div>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="alert-error" role="alert" aria-live="assertive">
                <AlertCircleIcon size={20} className="alert-error-icon" />
                <div>
                  <strong>{language === "te" ? "API பிழை" : "API Error"}</strong>
                  <div style={{ marginTop: 4 }}>{error}</div>
                </div>
              </div>
            )}
          </div>
        </form>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════
     RESULTS VIEW
  ══════════════════════════════════════════════════════════ */
  function ResultsView() {
    if (!result) {
      return (
        <div className="card" style={{ maxWidth: 480 }}>
          <div className="card-body">
            <div className="empty-state">
              <div className="empty-icon-wrap">
                <SparklesIcon size={26} />
              </div>
              <div className="empty-title">
                {language === "te" ? "ఇంకా అంచనా లేదు" : "No assessment yet"}
              </div>
              <div className="empty-desc">
                {language === "te"
                  ? "పంట సిఫార్సులు మరియు సలహా చూడటానికి అంచనా వేయండి."
                  : "Run a farm assessment to see crop recommendations and advisory here."}
              </div>
              <button
                className="btn-next"
                style={{ marginTop: 8 }}
                onClick={() => setView("assessment")}
              >
                <span>{t.runAssessmentBtn}</span>
                <ArrowRightIcon size={14} />
              </button>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="results-panel">
        {/* Topbar */}
        <div className="results-topbar">
          <div>
            <h1 className="results-heading">{t.assessmentDone}</h1>
            <div className="results-meta">
              <span>ID: <code>{result.assessment_id.slice(0, 12)}…</code></span>
              <span>·</span>
              <span>
                {language === "te" ? "వাতාவరణ వనరు:" : "Weather:"}
                <span className="source-tag" style={{ marginLeft: 4 }}>{result.weather_source}</span>
              </span>
              <span>·</span>
              <span>
                {language === "te" ? "నిల్వ:" : "Storage:"}
                <span className="source-tag" style={{ marginLeft: 4 }}>{result.storage}</span>
              </span>
            </div>
          </div>
          <button className="btn-export" onClick={openReportConfirmation} id="btn-export-pdf">
            <FileTextIcon size={16} />
            <span>{t.exportBtn}</span>
          </button>
        </div>

        {/* Storage notice */}
        <div className="storage-info-strip">
          <InfoIcon size={14} className="storage-icon" />
          <span>
            {storageMode === "sqlite_local"
              ? (language === "te"
                  ? "నిల్వ: SQLite లోకల్ డేటాబేస్ — ఈ నివేదిక సర్వర్ రీస్టార్ట్ తర్వాత కూడా భద్రపరచబడి ఉంటుంది (.tmp/kshetraiq.db)."
                  : "Storage: SQLite Local Database — This assessment is safely persisted across server restarts in .tmp/kshetraiq.db.")
              : t.storageNotice}
          </span>
        </div>

        {/* Crop Recommendation Hero */}
        {prediction ? (
          <div className="crop-hero-card">
            <div className="crop-hero-header">
              <div>
                <div className="model-badge">VERIFIED ML CROP RECOMMENDATION</div>
                <div className="crop-name-primary">
                  {language === "te"
                    ? prediction.recommended_crop_te
                    : prediction.recommended_crop.toUpperCase()}
                </div>
                <div className="crop-name-secondary">
                  {language === "te"
                    ? prediction.recommended_crop
                    : prediction.recommended_crop_te}
                </div>
                <div className="algo-tag">{prediction.algorithm}</div>
              </div>
              <div className="confidence-section">
                <span className="conf-label">{t.confidenceLbl}</span>
                <span className="conf-percent">
                  {Math.round(prediction.confidence * 100)}%
                </span>
                <div className="conf-bar-track" style={{ width: 100 }}>
                  <div
                    className="conf-bar-fill"
                    style={{ width: `${Math.round(prediction.confidence * 100)}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Features used */}
            <div className="features-row">
              <span className="features-label">
                {language === "te" ? "మోడల్ ఇన్‌పుట్‌లు:" : "Verified inputs:"}
              </span>
              {Object.entries(prediction.features_used).map(([k, v]) => (
                <span key={k} className="feature-chip">
                  {k}: <strong>{v}</strong>
                </span>
              ))}
            </div>

            {/* Alternatives */}
            {prediction.top_candidates && prediction.top_candidates.length > 1 && (
              <div className="alternatives-section">
                <div className="alt-section-title">{t.altsTitle}</div>
                <div className="alt-items">
                  {prediction.top_candidates.slice(1, 4).map((c) => (
                    <div key={c.crop} className="alt-item">
                      <span className="alt-name">
                        {language === "te" ? c.crop_te : c.crop}
                      </span>
                      <div className="alt-track">
                        <div
                          className="alt-fill"
                          style={{
                            width: `${Math.max(4, Math.round(c.confidence * 100))}%`,
                          }}
                        />
                      </div>
                      <span className="alt-pct">{Math.round(c.confidence * 100)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="needs-input-card">
            <AlertCircleIcon size={22} />
            <div>
              <h4>{cropModel?.message || "Crop recommendation needs verified inputs."}</h4>
              {cropModel?.missing_inputs && cropModel.missing_inputs.length > 0 && (
                <p>
                  {language === "te" ? "అవసరమైన ఫీల్డ్‌లు:" : "Missing fields:"}{" "}
                  <code>{cropModel.missing_inputs.join(", ")}</code>
                </p>
              )}
            </div>
          </div>
        )}

        {/* Advisor */}
        {result.advisor && (
          <div className="advisor-panel">
            <div className="advisor-header">
              <div>
                <div className="advisor-mode-chip">{result.advisor.provider_note}</div>
                <div className="advisor-title" style={{ marginTop: 6 }}>{t.advisorHeading}</div>
              </div>
            </div>
            <div className="advisor-lead">
              {language === "te" ? result.advisor.summary_te : result.advisor.summary}
            </div>
            <div className="advisor-quad">
              <article className="quad-card">
                <div className="quad-header">
                  <FlaskIcon size={16} />
                  <span className="quad-title">{t.soilHealthTitle}</span>
                </div>
                <div className="ph-status-row">
                  <span className="ph-status-label">pH Status:</span>
                  <span className="ph-status-value">
                    {result.advisor.soil_health_assessment.ph_status}
                  </span>
                </div>
                <p className="quad-body">
                  {language === "te"
                    ? result.advisor.soil_health_assessment.ph_note_te
                    : result.advisor.soil_health_assessment.ph_note}
                </p>
                <ul className="quad-bullets">
                  {(language === "te"
                    ? result.advisor.soil_health_assessment.npk_observations_te
                    : result.advisor.soil_health_assessment.npk_observations
                  ).map((obs, i) => (
                    <li key={i}>{obs}</li>
                  ))}
                </ul>
              </article>

              <article className="quad-card">
                <div className="quad-header">
                  <LeafIcon size={16} />
                  <span className="quad-title">{t.cropMgtTitle}</span>
                </div>
                <p className="quad-body">
                  {language === "te"
                    ? result.advisor.crop_guidance.best_practices_te
                    : result.advisor.crop_guidance.best_practices}
                </p>
              </article>

              <article className="quad-card">
                <div className="quad-header">
                  <CloudSunIcon size={16} />
                  <span className="quad-title">{t.waterMgtTitle}</span>
                </div>
                <p className="quad-body">
                  {language === "te"
                    ? result.advisor.water_and_irrigation.recommendation_te
                    : result.advisor.water_and_irrigation.recommendation}
                </p>
              </article>

              <article className="quad-card">
                <div className="quad-header">
                  <ShieldCheckIcon size={16} />
                  <span className="quad-title">{t.riskTitle}</span>
                </div>
                <ul className="quad-bullets">
                  {(language === "te"
                    ? result.advisor.seasonal_risk_management_te
                    : result.advisor.seasonal_risk_management
                  ).map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </article>
            </div>
            <div className="advisor-disclaimer">
              <InfoIcon size={13} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>{result.advisor.disclaimer}</span>
            </div>
          </div>
        )}

        {/* Predictive Agricultural Intelligence Suite */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><TrendingUpIcon size={18} /></span>
              {language === "te" ? "ముందస్తు వ్యవసాయ విశ్లేషణలు (ML సూట్)" : "Advanced Predictive Agricultural Intelligence (ML Suite)"}
            </span>
          </div>
          <div className="card-body">
            {/* Tool 1: Crop Yield Predictor */}
            <div style={{ padding: 18, background: "var(--page-bg)", borderRadius: "var(--r-md)", marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--green-950)" }}>
                    🌾 {language === "te" ? "పంట దిగుబడి అంచనా (Random Forest ML)" : "Crop Yield Prediction (Random Forest Regressor)"}
                  </div>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 2 }}>
                    Validated Scikit-Learn Pipeline · $R^2 = 0.9802$ · Model ID: <code>crop-yield-v1</code>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <select
                    value={yieldCrop}
                    onChange={(e) => setYieldCrop(e.target.value)}
                    style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid var(--border)", fontSize: "0.82rem" }}
                  >
                    {["Rice", "Maize", "Cotton", "Groundnut", "Wheat", "Sugarcane", "Moong", "Urad"].map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  <button
                    className="card-action-btn"
                    onClick={handlePredictYield}
                    disabled={yieldLoading}
                    id="btn-predict-yield"
                  >
                    {yieldLoading ? "Calculating…" : (language === "te" ? "దిగుబడి లెక్కించండి" : "Predict Yield")}
                  </button>
                </div>
              </div>

              {yieldError && (
                <div style={{ color: "var(--red-text)", fontSize: "0.8rem", marginTop: 10 }}>
                  {yieldError}
                </div>
              )}

              {yieldResult && (
                <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, padding: 12, background: "var(--card-bg)", borderRadius: 8, border: "1px solid var(--border)" }}>
                  <div>
                    <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                      {language === "te" ? "హెక్టారుకు అంచనా దిగుబడి" : "Predicted Yield"}
                    </span>
                    <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--green-950)", marginTop: 2 }}>
                      {yieldResult.predicted_yield_tonnes_per_hectare} <span style={{ fontSize: "0.85rem", fontWeight: 500 }}>Tons/Ha</span>
                    </div>
                  </div>
                  <div>
                    <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                      {language === "te" ? "మొత్తం ఉత్పత్తి" : "Estimated Total Production"}
                    </span>
                    <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--green-800)", marginTop: 2 }}>
                      {yieldResult.predicted_total_production_tonnes} <span style={{ fontSize: "0.85rem", fontWeight: 500 }}>Tons</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Tool 2: Climate Scenario Analysis */}
            <div style={{ padding: 18, background: "var(--page-bg)", borderRadius: "var(--r-md)", marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--green-950)" }}>
                    🌦️ {language === "te" ? "వాతావరణ మార్పు ప్రభావ విశ్లేషణ" : "Climate Change Scenario & Drought Stress-Test"}
                  </div>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 2 }}>
                    Simulates crop yield sensitivity under -10% and -25% seasonal precipitation shocks
                  </div>
                </div>
                <button
                  className="card-action-btn"
                  onClick={handlePredictClimate}
                  disabled={climateLoading}
                  id="btn-simulate-climate"
                >
                  {climateLoading ? "Simulating…" : (language === "te" ? "వాతావరణ ముప్పు పరీక్షించండి" : "Simulate Drought Scenarios")}
                </button>
              </div>

              {climateError && (
                <div style={{ color: "var(--red-text)", fontSize: "0.8rem", marginTop: 10 }}>
                  {climateError}
                </div>
              )}

              {climateResult && (
                <div style={{ marginTop: 14 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10 }}>
                    <div style={{ padding: 10, background: "var(--card-bg)", borderRadius: 6, border: "1px solid var(--border)" }}>
                      <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>Baseline Yield</span>
                      <div style={{ fontSize: "1.2rem", fontWeight: 700 }}>{climateResult.baseline_yield_tonnes_per_ha} t/ha</div>
                    </div>
                    <div style={{ padding: 10, background: "var(--card-bg)", borderRadius: 6, border: "1px solid var(--border)" }}>
                      <span style={{ fontSize: "0.7rem", color: "var(--amber-text)" }}>-10% Rain ({climateResult.moderate_change_percent}%)</span>
                      <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--amber-text)" }}>
                        {climateResult.moderate_shock_yield_tonnes_per_ha} t/ha
                      </div>
                    </div>
                    <div style={{ padding: 10, background: "var(--card-bg)", borderRadius: 6, border: "1px solid var(--border)" }}>
                      <span style={{ fontSize: "0.7rem", color: "var(--red-text)" }}>-25% Drought ({climateResult.severe_change_percent}%)</span>
                      <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--red-text)" }}>
                        {climateResult.severe_shock_yield_tonnes_per_ha} t/ha
                      </div>
                    </div>
                  </div>
                  <div style={{ marginTop: 10, padding: 10, background: "var(--green-50)", borderRadius: 6, fontSize: "0.82rem", color: "var(--green-900)" }}>
                    <strong>Agronomic Advice:</strong> {climateResult.recommendation}
                  </div>
                </div>
              )}
            </div>

            {/* Tool 3: Sustainability Score */}
            <div style={{ padding: 18, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--green-950)" }}>
                    🌱 {language === "te" ? "సుస్థిర వ్యవసాయ స్కోరు (0–100)" : "Agronomic Sustainability Scoring"}
                  </div>
                  <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginTop: 2 }}>
                    Evaluates chemical input intensity vs yield efficiency according to ICAR benchmarks
                  </div>
                </div>
                <button
                  className="card-action-btn"
                  onClick={handleCalculateSustainability}
                  disabled={sustainabilityLoading}
                  id="btn-calc-sustainability"
                >
                  {sustainabilityLoading ? "Scoring…" : (language === "te" ? "స్కోరు లెక్కించండి" : "Calculate Sustainability")}
                </button>
              </div>

              {sustainabilityError && (
                <div style={{ color: "var(--red-text)", fontSize: "0.8rem", marginTop: 10 }}>
                  {sustainabilityError}
                </div>
              )}

              {sustainabilityResult && (
                <div style={{ marginTop: 14 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 14, padding: 12, background: "var(--card-bg)", borderRadius: 8, border: "1px solid var(--border)" }}>
                    <div style={{ fontSize: "2rem", fontWeight: 800, color: "var(--green-700)" }}>
                      {sustainabilityResult.score}
                      <span style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>/100</span>
                    </div>
                    <div>
                      <span className={`status-chip ${sustainabilityResult.category.includes("High") ? "live" : "pending"}`}>
                        {sustainabilityResult.category}
                      </span>
                      <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: 4 }}>
                        {sustainabilityResult.advisory_notes?.[0]}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Model Registry — results context */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><DatabaseIcon size={16} /></span>
              {language === "te" ? "AI మోడల్ రిజిస్ట్రీ స్థితి" : "AI Model Registry Audit"}
            </span>
          </div>
          <div className="registry-results-grid">
            {result.results.map((item) => (
              <div key={item.model_id} className="registry-result-card">
                <div className="reg-card-top">
                  <span className="reg-model-id">{item.model_id}</span>
                  <span className={`reg-status ${item.status}`}>
                    {item.status.toUpperCase()}
                  </span>
                </div>
                <div className="reg-card-desc">{item.message}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════
     FARM PROFILE VIEW
  ══════════════════════════════════════════════════════════ */
  function ProfileView() {
    const farmerDisplayName = authUser?.display_name || globalUser?.full_name || (language === "te" ? "రైతు" : "Registered Farmer");
    const farmerEmail = authUser?.email || globalUser?.email || "—";
    const farmerPhone = (globalUser as any)?.phone_number || "—";

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 840, width: "100%" }}>
        {/* Farmer Personal & Account Profile */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><UserIcon size={18} /></span>
              {language === "te" ? "రైతు వ్యక్తిగత ఖాతా" : "Farmer Account & Identity"}
            </span>
            <span className="status-chip ready" style={{ fontSize: "0.72rem" }}>
              {language === "te" ? "ధృవీకరించబడిన ఖాతా" : "Verified Account"}
            </span>
          </div>
          <div className="card-body">
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {language === "te" ? "రైతు పేరు" : "Farmer Name"}
                </div>
                <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--green-950)", marginTop: 4 }}>
                  {farmerDisplayName}
                </div>
              </div>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {language === "te" ? "ఈమెయిల్ చిరునామా" : "Email Address"}
                </div>
                <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--green-950)", marginTop: 4 }}>
                  {farmerEmail}
                </div>
              </div>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {language === "te" ? "ఫోన్ నంబర్" : "Phone Number"}
                </div>
                <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "var(--green-950)", marginTop: 4 }}>
                  {farmerPhone}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Agricultural Holding Profile */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><LeafIcon size={18} /></span>
              {language === "te" ? "పొలం & కార్యాచరణ ప్రొఫైల్" : "Farm & Holding Operational Profile"}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {profileLoading && (
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  {language === "te" ? "లోడ్ అవుతోంది..." : "Loading…"}
                </span>
              )}
              <button
                className="card-action-btn"
                onClick={() => { setProfileNotice(""); setProfileEditing((prev) => !prev); }}
                type="button"
              >
                {profileEditing
                  ? (language === "te" ? "రద్దు చేయండి" : "Close Form")
                  : (language === "te" ? "సవరించండి" : "Edit Profile")}
              </button>
            </div>
          </div>
          <div className="card-body">
            {profileEditing && (
              <div style={{ padding: 16, background: "var(--page-bg)", borderRadius: "var(--r-md)", border: "1px solid var(--border)", marginBottom: 20 }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
                  <label style={{ display: "grid", gap: 6, fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)" }}>
                    Farm / Holding Name
                    <input
                      className="form-input"
                      type="text"
                      value={farmName}
                      onChange={(event) => setFarmName(event.target.value)}
                      placeholder="e.g. Sri Venkateswara Farm"
                    />
                  </label>
                  <label style={{ display: "grid", gap: 6, fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)" }}>
                    Land Area (Acres)
                    <input
                      className="form-input"
                      type="number"
                      step="0.1"
                      min="0.1"
                      value={acreage}
                      onChange={(event) => setAcreage(event.target.value)}
                      placeholder="e.g. 5.0"
                    />
                  </label>
                  <label style={{ display: "grid", gap: 6, fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)" }}>
                    Agricultural Season
                    <select
                      className="form-select"
                      value={season}
                      onChange={(event) => setSeason(event.target.value)}
                    >
                      <option value="Kharif">Kharif (Monsoon: Jun – Oct)</option>
                      <option value="Rabi">Rabi (Winter: Nov – Apr)</option>
                      <option value="Zaid">Zaid (Summer: Mar – Jun)</option>
                      <option value="Perennial">Perennial (Year-round)</option>
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: 6, fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)" }}>
                    Irrigation Method
                    <select
                      className="form-select"
                      value={irrigation}
                      onChange={(event) => setIrrigation(event.target.value)}
                    >
                      <option value="Drip">Drip Irrigation (High efficiency)</option>
                      <option value="Sprinkler">Sprinkler Irrigation</option>
                      <option value="Canal">Canal Irrigation</option>
                      <option value="Borewell">Borewell / Tube Well</option>
                      <option value="Flood">Flood / Furrow</option>
                      <option value="Rainfed">Rainfed (Dryland)</option>
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: 6, fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)" }}>
                    Water Availability
                    <select
                      className="form-select"
                      value={water}
                      onChange={(event) => setWater(event.target.value)}
                    >
                      <option value="Borewell">Borewell</option>
                      <option value="Canal">Canal</option>
                      <option value="Rainfed">Rainfed</option>
                      <option value="River">River</option>
                      <option value="Pond">Pond / Farm Pond</option>
                      <option value="Tank">Tank / Reservoir</option>
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: 6, fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)" }}>
                    State
                    <select className="form-select" value={state} onChange={(event) => selectState(event.target.value)}>
                      <option value="">Select a state</option>
                      {SUPPORTED_STATES.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label style={{ display: "grid", gap: 6, fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)" }}>
                    District
                    <select className="form-select" value={district} disabled={!state} onChange={(event) => setDistrict(event.target.value)}>
                      <option value="">{state ? "Select a district" : "Select state first"}</option>
                      {districtChoices.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <div style={{ gridColumn: "1 / -1", display: "flex", gap: 10, marginTop: 8 }}>
                    <button className="btn-next" type="button" disabled={profileSaving} onClick={saveFarmProfile}>
                      {profileSaving ? (language === "te" ? "భద్రపరుస్తోంది..." : "Saving…") : (language === "te" ? "మార్పులను భద్రపరచండి" : "Save Changes")}
                    </button>
                    <button
                      className="btn-back"
                      type="button"
                      onClick={() => {
                        if (savedFarmProfile) applyFarmProfile(savedFarmProfile);
                        setProfileEditing(false);
                        setProfileNotice("");
                      }}
                    >
                      {language === "te" ? "రద్దు" : "Cancel"}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {profileNotice && (
              <div style={{ padding: "10px 14px", background: "var(--green-50)", border: "1px solid var(--green-200)", borderRadius: "var(--r-md)", fontSize: "0.82rem", color: "var(--green-900)", marginBottom: 16 }}>
                {profileNotice}
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 14 }}>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {t.farmNameLbl}
                </div>
                <div style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--green-950)", marginTop: 4 }}>
                  {farmName || "—"}
                </div>
              </div>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {language === "te" ? "భౌగోళిక స్థానం" : "Location"}
                </div>
                <div style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--green-950)", marginTop: 4 }}>
                  {district && state ? `${district}, ${state}` : (state || district || "—")}
                </div>
              </div>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {t.acreageLbl}
                </div>
                <div style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--green-950)", marginTop: 4 }}>
                  {acreage ? `${acreage} Acres` : "—"}
                </div>
              </div>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {t.seasonLbl}
                </div>
                <div style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--green-950)", marginTop: 4 }}>
                  {season || "Kharif"}
                </div>
              </div>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {t.irrigationLbl}
                </div>
                <div style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--green-950)", marginTop: 4 }}>
                  {irrigation || "—"}
                </div>
              </div>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {t.waterLbl}
                </div>
                <div style={{ fontSize: "1.05rem", fontWeight: 600, color: "var(--green-950)", marginTop: 4 }}>
                  {water || "—"}
                </div>
              </div>
            </div>

            <div style={{ marginTop: 22, display: "flex", gap: 12 }}>
              <button
                className="btn-next"
                onClick={() => { setView("assessment"); setActiveStep(1); }}
                type="button"
              >
                <span>{t.runAssessmentBtn}</span>
                <ArrowRightIcon size={14} />
              </button>
              {result && (
                <button
                  className="btn-back"
                  onClick={openReportConfirmation}
                  type="button"
                >
                  {t.exportBtn}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════
     WEATHER VIEW
  ══════════════════════════════════════════════════════════ */
  function WeatherView() {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 840 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><CloudSunIcon size={18} /></span>
              {language === "te" ? "ఓపెన్-మెటియో ప్రత్యక్ష వాతావరణం" : "Open-Meteo Agro-Climatic Intelligence"}
            </span>
            <button
              className="btn-fetch"
              onClick={handleWeatherFetch}
              disabled={fetchingWeather}
            >
              <RefreshIcon size={14} className={fetchingWeather ? "spin" : ""} />
              <span>{fetchingWeather ? t.fetchingBtn : t.fetchWeatherBtn}</span>
            </button>
          </div>
          <div className="card-body">
            {(!district || !state) && (
              <div className="empty-state">
                <CloudSunIcon size={28} />
                <div className="empty-title">{language === "te" ? "జిల్లా నమోదు చేయండి" : "Set Your Farm Location"}</div>
                <div className="empty-desc">
                  {language === "te"
                    ? "వాతావరణ సమాచారం పొందడానికి ముందు ప్రొఫైల్‌లో రాష్ట్రం మరియు జిల్లాను నమోదు చేయండి."
                    : "Please save your State and District in Farm Profile first, then return here to fetch live weather."}
                </div>
              </div>
            )}
            {district && state && (
              <>
                {dashWeather ? (
                  <>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 16 }}>
                      <div style={{ padding: 20, background: "var(--blue-bg)", borderRadius: "var(--r-md)", textAlign: "center" }}>
                        <div style={{ fontSize: "0.8rem", color: "var(--blue-text)", fontWeight: 600 }}>{t.tempLbl}</div>
                        <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--green-950)", marginTop: 6 }}>
                          {dashWeather.temp}°C
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>Ambient Field Temp</div>
                      </div>
                      <div style={{ padding: 20, background: "var(--blue-bg)", borderRadius: "var(--r-md)", textAlign: "center" }}>
                        <div style={{ fontSize: "0.8rem", color: "var(--blue-text)", fontWeight: 600 }}>{t.humidityLbl}</div>
                        <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--green-950)", marginTop: 6 }}>
                          {dashWeather.humidity}%
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>Relative Humidity</div>
                      </div>
                      <div style={{ padding: 20, background: "var(--blue-bg)", borderRadius: "var(--r-md)", textAlign: "center" }}>
                        <div style={{ fontSize: "0.8rem", color: "var(--blue-text)", fontWeight: 600 }}>{t.rainfallLbl}</div>
                        <div style={{ fontSize: "2.2rem", fontWeight: 700, color: "var(--green-950)", marginTop: 6 }}>
                          {dashWeather.rainfall} mm
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 4 }}>Seasonal Estimate</div>
                      </div>
                    </div>
                    <div style={{ marginTop: 10, fontSize: "0.78rem", color: "var(--green-700)", fontWeight: 600 }}>
                      📍 {dashWeather.district}, {state} — {dashWeather.source}
                    </div>
                  </>
                ) : (
                  <div className="empty-state">
                    <CloudSunIcon size={28} />
                    <div className="empty-title">{language === "te" ? "వాతావరణం లోడ్ కాలేదు" : "Weather Not Loaded"}</div>
                    <div className="empty-desc">
                      {language === "te"
                        ? "జిల్లా వాతావరణ సమాచారం పొందడానికి పైన ఉన్న బటన్ క్లిక్ చేయండి."
                        : "Click the refresh button above to fetch live Open-Meteo observations for your district."}
                    </div>
                    <div className="empty-desc" style={{ marginTop: 8, fontSize: "0.78rem", color: "var(--amber-text)" }}>
                      Note: Open-Meteo enforces a free-tier daily request limit. If weather fails, try again after a few minutes or enter values manually in the Assessment form.
                    </div>
                  </div>
                )}
              </>
            )}
            <div style={{ marginTop: 16, fontSize: "0.8rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 6 }}>
              <InfoIcon size={14} />
              <span>
                {language === "te"
                  ? "వనరు: ఓపెన్-మెటియో లైవ్ సర్వీస్. రైతు అవసరమైతే అసెస్‌మెంట్‌లో మాన్యువల్ విలువలు నమోదు చేసుకోవచ్చు."
                  : "Source: Open-Meteo live API (free tier, no key required). If rate-limited, weather data is served from an in-memory cache for the current session."}
              </span>
            </div>
          </div>
        </div>

        {/* XGBoost Weather Risk Prediction Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><ShieldCheckIcon size={18} /></span>
              {language === "te" ? "వాతావరణ ముప్పు విశ్లేషణ (XGBoost ML)" : "Agro-Climatic Weather Risk Assessment (XGBoost ML)"}
            </span>
            <button
              className="card-action-btn"
              onClick={handlePredictWeatherRisk}
              disabled={weatherRiskLoading}
              id="btn-evaluate-weather-risk"
            >
              {weatherRiskLoading
                ? (language === "te" ? "విశ్లేషిస్తున్నాం..." : "Evaluating Risk…")
                : (language === "te" ? "ముప్పు అంచనా వేయండి" : "Evaluate Weather Risk")}
            </button>
          </div>
          <div className="card-body">
            {weatherRiskError && (
              <div style={{ padding: 12, background: "var(--red-bg)", color: "var(--red-text)", borderRadius: "var(--r-md)", fontSize: "0.85rem", marginBottom: 16 }}>
                {weatherRiskError}
              </div>
            )}
            {weatherRiskResult ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                  <div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600 }}>
                      {language === "te" ? "అంచనా వేయబడిన రిస్క్ స్థాయి" : "Calculated Risk Level"}
                    </div>
                    <div style={{ fontSize: "1.4rem", fontWeight: 700, color: "var(--green-950)", marginTop: 4 }}>
                      {weatherRiskResult.predicted_risk_level}
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      {language === "te" ? "మోడల్ విశ్వసనీయత" : "Model Confidence"}
                    </div>
                    <div style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--green-700)" }}>
                      {Math.round(weatherRiskResult.confidence * 100)}%
                    </div>
                  </div>
                </div>

                <div style={{ padding: 14, background: "var(--green-50)", color: "var(--green-950)", borderRadius: "var(--r-md)", fontSize: "0.85rem", border: "1px solid var(--green-200)" }}>
                  <strong>{language === "te" ? "వాతావరణ సలహా:" : "Agro-Meteorological Advisory:"}</strong> {weatherRiskResult.advisory}
                </div>

                <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", borderTop: "1px solid var(--border)", paddingTop: 8 }}>
                  Engine: <code>weather_risk_xgboost_model.pkl</code> (8 features: Temp, Humidity, Precip, Wind, Pressure, Season, Month, State)
                </div>
              </div>
            ) : (
              <div className="empty-state">
                <ShieldCheckIcon size={26} />
                <div className="empty-desc" style={{ marginTop: 8 }}>
                  {language === "te"
                    ? "ఓపెన్-మెటియో కొలతలను ఉపయోగించి ఫీల్డ్-లెవల్ వాతావరణ ప్రమాదాన్ని లెక్కించడానికి 'ముప్పు అంచనా వేయండి' క్లిక్ చేయండి."
                    : "Click 'Evaluate Weather Risk' to run XGBoost risk classification using real field meteorological observations."}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════
     SOIL HEALTH VIEW (Score out of 100, 5 Bands, Recommendations)
  ══════════════════════════════════════════════════════════ */
  function SoilHealthView() {
    const soilAssessment = soilScoreResult || result?.advisor?.soil_health_assessment;
    const scoreVal = soilAssessment?.score != null ? Math.round(soilAssessment.score) : null;
    const category = soilAssessment?.category || "Not assessed";
    const categoryTe = soilAssessment?.category_te || category;

    // 5 Bands: 80-100 Excellent, 60-79 Good, 40-59 Moderate, 20-39 Poor, 0-19 Critical
    const getBandColor = (score: number | null) => {
      if (score === null) return { bg: "#f3f4f6", border: "#e5e7eb", text: "#6b7280", ring: "#9ca3af", label: "Not Assessed" };
      if (score >= 80) return { bg: "#ecfdf5", border: "#a7f3d0", text: "#065f46", ring: "#10b981", label: "Excellent" };
      if (score >= 60) return { bg: "#f0fdfa", border: "#99f6e4", text: "#115e59", ring: "#0d9488", label: "Good" };
      if (score >= 40) return { bg: "#fffbeb", border: "#fde68a", text: "#92400e", ring: "#f59e0b", label: "Moderate" };
      if (score >= 20) return { bg: "#fff7ed", border: "#fed7aa", text: "#9a3412", ring: "#ea580c", label: "Poor" };
      return { bg: "#fef2f2", border: "#fecaca", text: "#991b1b", ring: "#ef4444", label: "Critical" };
    };

    const bandTheme = getBandColor(scoreVal);
    const recommendationsList = (language === "te" ? soilAssessment?.recommendations_te : soilAssessment?.recommendations) || [];

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 880 }}>
        <div className="card">
          <div className="card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
            <span className="card-title">
              <span className="card-title-icon"><FlaskIcon size={18} /></span>
              {t.soilHealthTitle}
            </span>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="btn-next"
                style={{ padding: "8px 16px", fontSize: "0.85rem", display: "inline-flex", alignItems: "center", gap: 6, background: "var(--green-700)", color: "white" }}
                onClick={handleCalculateSoilScore}
                disabled={calculatingSoilScore}
                type="button"
                id="btn-calculate-soil-score"
              >
                <FlaskIcon size={14} />
                <span>{calculatingSoilScore ? (language === "te" ? "గణిస్తోంది..." : "Calculating...") : (language === "te" ? "నేల స్కోరు లెక్కించండి" : "Calculate Soil Health Score")}</span>
              </button>
              <button
                className="card-action-btn"
                onClick={() => { setView("assessment"); setActiveStep(2); }}
              >
                {language === "te" ? "ల్యాబ్ విలువలు సవరించండి" : "Update Lab Values"}
              </button>
            </div>
          </div>
          <div className="card-body">
            {soilScoreError && (
              <div style={{ padding: "10px 14px", background: "var(--red-bg)", borderRadius: "var(--r-md)", fontSize: "0.82rem", color: "var(--red-text)", marginBottom: 16 }}>
                {soilScoreError}
              </div>
            )}

            {/* Score Banner with Circular Gauge & Band Info */}
            {scoreVal !== null ? (
              <div style={{ padding: 18, marginBottom: 18, background: bandTheme.bg, borderRadius: "var(--r-md)", border: `1.5px solid ${bandTheme.border}` }}>
                <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap" }}>
                  <div style={{
                    width: 96, height: 96, borderRadius: "50%", display: "grid", placeItems: "center",
                    background: bandTheme.ring, color: "white", textAlign: "center", flexShrink: 0,
                    boxShadow: "0 4px 12px rgba(0,0,0,0.12)"
                  }}>
                    <div>
                      <div style={{ fontWeight: 800, fontSize: "1.55rem", lineHeight: 1 }}>{scoreVal}</div>
                      <div style={{ fontSize: "0.68rem", opacity: 0.9, marginTop: 2 }}>/ 100</div>
                    </div>
                  </div>
                  <div style={{ flex: 1, minWidth: 220 }}>
                    <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.08em", color: "var(--text-muted)", textTransform: "uppercase" }}>
                      SOIL HEALTH SCORE (0–100) · ICAR / ANGRAU STANDARDS
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 4 }}>
                      <span style={{ fontSize: "1.35rem", fontWeight: 800, color: bandTheme.text }}>
                        {language === "te" ? categoryTe : category}
                      </span>
                      <span style={{
                        fontSize: "0.7rem", fontWeight: 700, padding: "2px 8px", borderRadius: 12,
                        background: bandTheme.border, color: bandTheme.text, textTransform: "uppercase"
                      }}>
                        {bandTheme.label}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: 4, lineHeight: 1.4 }}>
                      {soilAssessment?.is_provisional
                        ? (language === "te" ? "తాత్కాలిక అంచనా: ప్రస్తుతం అందుబాటులో ఉన్న కొలతలతో లెక్కించబడింది." : "Provisional score: calculated using currently available parameters; missing measurements excluded.")
                        : (language === "te" ? "N, P, K మరియు pH ల్యాబ్ కొలతల ఆధారంగా పూర్తి విశ్లేషణ." : "Complete screening based on certified N, P, K, and pH observations.")}
                    </div>
                  </div>
                </div>

                {/* 5 Bands Visual Scale Indicator */}
                <div style={{ marginTop: 16, paddingTop: 14, borderTop: `1px solid ${bandTheme.border}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.7rem", fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>
                    <span>0 Critical</span>
                    <span>20 Poor</span>
                    <span>40 Moderate</span>
                    <span>60 Good</span>
                    <span>80 Excellent 100</span>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr", gap: 3, height: 10, borderRadius: 6, overflow: "hidden" }}>
                    <div title="Critical: 0-19" style={{ background: "#ef4444", opacity: scoreVal < 20 ? 1 : 0.45 }} />
                    <div title="Poor: 20-39" style={{ background: "#ea580c", opacity: scoreVal >= 20 && scoreVal < 40 ? 1 : 0.45 }} />
                    <div title="Moderate: 40-59" style={{ background: "#f59e0b", opacity: scoreVal >= 40 && scoreVal < 60 ? 1 : 0.45 }} />
                    <div title="Good: 60-79" style={{ background: "#0d9488", opacity: scoreVal >= 60 && scoreVal < 80 ? 1 : 0.45 }} />
                    <div title="Excellent: 80-100" style={{ background: "#10b981", opacity: scoreVal >= 80 ? 1 : 0.45 }} />
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ padding: 18, marginBottom: 18, background: "var(--page-bg)", borderRadius: "var(--r-md)", border: "1px dashed var(--border)", textAlign: "center" }}>
                <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 10 }}>
                  {language === "te"
                    ? "ఖచ్చితమైన నేల ఆరోగ్యం స్కోరు (0-100) పొందడానికి దిగువ బటన్‌ను క్లిక్ చేయండి."
                    : "Calculate your 0–100 Soil Health Score across 5 verified agronomic bands."}
                </div>
                <button
                  className="btn-next"
                  style={{ display: "inline-flex", alignItems: "center", gap: 6, background: "var(--green-700)", color: "white" }}
                  onClick={handleCalculateSoilScore}
                  disabled={calculatingSoilScore}
                  type="button"
                >
                  <FlaskIcon size={14} />
                  <span>{calculatingSoilScore ? (language === "te" ? "గణిస్తోంది..." : "Calculating...") : (language === "te" ? "నేల స్కోరు లెక్కించండి" : "Calculate Soil Health Score")}</span>
                </button>
              </div>
            )}

            {/* 4 Nutrient Diagnostics Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginTop: 12 }}>
              {[
                { sym: "N", name: "Nitrogen", nameTe: "నత్రజని", val: nitrogen, unit: "kg/ha", range: "280–560 kg/ha", cls: "n", paramKey: "nitrogen_kg_ha" },
                { sym: "P", name: "Phosphorus", nameTe: "భాస్వరం", val: phosphorus, unit: "kg/ha", range: "10–25 kg/ha", cls: "p", paramKey: "phosphorus_kg_ha" },
                { sym: "K", name: "Potassium", nameTe: "పొటాషియం", val: potassium, unit: "kg/ha", range: "120–280 kg/ha", cls: "k", paramKey: "potassium_kg_ha" },
                { sym: "pH", name: "Soil pH", nameTe: "నేల pH", val: ph, unit: "0–14", range: "6.5–7.5", cls: "ph", paramKey: "ph" },
              ].map((item) => {
                const paramObj = soilAssessment?.parameters?.[item.paramKey];
                const status = paramObj?.status || "measured";
                const statusBadgeBg = status === "optimal" ? "#d1fae5" : status === "low" ? "#fef3c7" : status === "high" ? "#ede9fe" : "#f3f4f6";
                const statusBadgeColor = status === "optimal" ? "#065f46" : status === "low" ? "#92400e" : status === "high" ? "#5b21b6" : "#4b5563";
                const statusText = status === "optimal"
                  ? (language === "te" ? "సరైనది" : "Optimal")
                  : status === "low"
                  ? (language === "te" ? "లోపం" : "Deficient")
                  : status === "high"
                  ? (language === "te" ? "అధికం" : "High")
                  : status;

                return (
                  <div key={item.sym} style={{
                    padding: 12, borderRadius: "var(--r-md)", border: "1px solid var(--border)",
                    background: "white", display: "flex", flexDirection: "column", gap: 6
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "var(--green-900)" }}>
                        {item.sym} <small style={{ fontWeight: 500, fontSize: "0.75rem", color: "var(--text-muted)" }}>({language === "te" ? item.nameTe : item.name})</small>
                      </span>
                      <span style={{ fontSize: "0.68rem", fontWeight: 700, padding: "2px 6px", borderRadius: 4, background: statusBadgeBg, color: statusBadgeColor, textTransform: "capitalize" }}>
                        {statusText}
                      </span>
                    </div>
                    <div style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--text-primary)" }}>
                      {item.val || "—"} <span style={{ fontSize: "0.72rem", fontWeight: 400, color: "var(--text-muted)" }}>{item.unit}</span>
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "auto" }}>
                      Ref: {item.range}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Agronomic Recommendations */}
            {recommendationsList.length > 0 && (
              <div style={{ marginTop: 20, padding: 16, background: "var(--page-bg)", borderRadius: "var(--r-md)", border: "1px solid var(--border)" }}>
                <div style={{ fontWeight: 700, color: "var(--green-950)", fontSize: "0.92rem", display: "flex", alignItems: "center", gap: 6 }}>
                  <LeafIcon size={16} />
                  {language === "te" ? "ఖచ్చితమైన వ్యవసాయ సూచనలు & పోషక నిర్వహణ:" : "Agronomic Diagnostics & Management Plan:"}
                </div>
                {soilAssessment?.ph_note && (
                  <div style={{ marginTop: 8, fontSize: "0.82rem", color: "var(--text-primary)", fontWeight: 500 }}>
                    {language === "te" ? (soilAssessment.ph_note_te || soilAssessment.ph_note) : soilAssessment.ph_note}
                  </div>
                )}
                <ul style={{ marginTop: 10, paddingLeft: 18, fontSize: "0.82rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                  {recommendationsList.map((rec: string, idx: number) => (
                    <li key={idx} style={{ marginTop: 5 }}>{rec}</li>
                  ))}
                </ul>
                <div style={{ marginTop: 12, fontSize: "0.7rem", color: "var(--text-muted)", borderTop: "1px dashed var(--border)", paddingTop: 8 }}>
                  ICAR / SAU screening standards. Local KVK / Soil Testing Laboratory results take precedence over broad screening ranges.
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><FileTextIcon size={18} /></span>
              {t.uploadSoilReportTitle}
            </span>
          </div>
          <div className="card-body">
            <FileUploadBox
              category="soil_report"
              title={language === "te" ? "సాయిల్ హెల్త్ కార్డు / అధికారిక ల్యాబ్ పత్రం" : "Soil Health Card or Certified Soil Lab Report"}
              subtitle={t.uploadHint}
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              onUpload={handleFileUpload}
              uploading={uploadingCategory === "soil_report"}
              files={uploadedFiles}
              onDelete={handleDeleteUpload}
              language={language}
            />
            {uploadError && uploadingCategory === "soil_report" && (
              <div style={{ color: "var(--red-text)", fontSize: "0.75rem", marginTop: 4 }}>
                {uploadError}
              </div>
            )}
            {uploadSuccessMsg && (
              <div style={{ color: "var(--green-700)", fontSize: "0.75rem", marginTop: 4 }}>
                {uploadSuccessMsg}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════
     IRRIGATION & WATER VIEW
  ══════════════════════════════════════════════════════════ */
  function IrrigationView() {
    const waterGuidance = result?.advisor?.water_and_irrigation;
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 840 }}>
        {/* Existing assessment-based advisory */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><DropletIcon size={18} /></span>
              {t.waterMgtTitle}
            </span>
          </div>
          <div className="card-body">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{t.irrigationLbl}</span>
                <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--green-950)", marginTop: 4 }}>
                  {irrigation}
                </div>
              </div>
              <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{t.waterLbl}</span>
                <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--green-950)", marginTop: 4 }}>
                  {water}
                </div>
              </div>
            </div>

            {waterGuidance ? (
              <div style={{ marginTop: 20, padding: 16, background: "var(--green-50)", borderRadius: "var(--r-md)", border: "1px solid var(--green-200)" }}>
                <div style={{ fontWeight: 600, color: "var(--green-900)", fontSize: "0.95rem" }}>
                  {language === "te" ? "శాస్త్రీయ నీటి నిర్వహణ సలహా:" : "Scientific Irrigation Scheduling Advisory:"}
                </div>
                <p style={{ marginTop: 8, fontSize: "0.85rem", color: "var(--text-primary)", lineHeight: 1.6 }}>
                  {language === "te" ? waterGuidance.recommendation_te : waterGuidance.recommendation}
                </p>
              </div>
            ) : (
              <div className="empty-state" style={{ marginTop: 16 }}>
                <div className="empty-desc">
                  {language === "te"
                    ? "నీటి నిర్వహణ సలహా చూడటానికి పొలం అంచనా ప్రారంభించండి."
                    : "Run an assessment to generate tailored water scheduling and drought mitigation guidance."}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ──── ICAR Water Budget Calculator ──── */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><DropletIcon size={18} /></span>
              {language === "te" ? "నీటిపారుదల సలహాదారు (RL PPO పాలసీ & ICAR బడ్జెటింగ్)" : "Irrigation Advisory (RL PPO Policy & ICAR Budgeting)"}
            </span>
          </div>
          <div className="card-body">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
              <label className="field-label">
                {language === "te" ? "పంట" : "Crop"}
                <select value={irrCrop} onChange={(e) => setIrrCrop(e.target.value)} className="form-select" id="irr-crop">
                  <option value="Rice">Rice (వరి)</option>
                  <option value="Cotton">Cotton (పత్తి)</option>
                  <option value="Maize">Maize (మొక్కజొన్న)</option>
                  <option value="Wheat">Wheat (గోధుమ)</option>
                  <option value="Sugarcane">Sugarcane (చెరకు)</option>
                  <option value="Groundnut">Groundnut (వేరుశెనగ)</option>
                  <option value="Chilli">Chilli (మిర్చి)</option>
                  <option value="Tomato">Tomato (టమాటా)</option>
                </select>
              </label>
              <label className="field-label">
                {language === "te" ? "పంట రోజులు" : "Crop Age (days)"}
                <input type="number" min="1" max="365" value={irrCropDays} onChange={(e) => setIrrCropDays(e.target.value)} className="form-input" id="irr-crop-days" />
              </label>
              <label className="field-label">
                {language === "te" ? "నేల తేమ" : "Soil Moisture (0-1000)"}
                <input type="number" min="0" max="1000" value={irrSoilMoisture} onChange={(e) => setIrrSoilMoisture(e.target.value)} className="form-input" id="irr-soil-moisture" />
              </label>
              <label className="field-label">
                {language === "te" ? "నేల రకం" : "Soil Type"}
                <select value={irrSoilType} onChange={(e) => setIrrSoilType(e.target.value)} className="form-select" id="irr-soil-type">
                  <option value="Loam">Loam (లోమ్)</option>
                  <option value="Clay">Clay (బంకమట్టి)</option>
                  <option value="Sandy">Sandy (ఇసుక)</option>
                  <option value="Black">Black (నల్లరేగడి)</option>
                </select>
              </label>
              <label className="field-label">
                {language === "te" ? "ఉష్ణోగ్రత (°C)" : "Temperature (°C)"}
                <input type="number" min="-10" max="55" step="0.5" value={irrTemp} onChange={(e) => setIrrTemp(e.target.value)} className="form-input" id="irr-temp" />
              </label>
              <label className="field-label">
                {language === "te" ? "వర్షపాతం అంచనా (mm)" : "3-Day Rainfall Forecast (mm)"}
                <input type="number" min="0" max="500" value={irrRainfallForecast} onChange={(e) => setIrrRainfallForecast(e.target.value)} className="form-input" id="irr-rainfall" />
              </label>
              <label className="field-label">
                {language === "te" ? "నేల ఉష్ణోగ్రత (°C - సెన్సార్)" : "Soil Temp (°C - Optional)"}
                <input type="number" min="-5" max="60" step="0.5" value={irrSoilTemp} onChange={(e) => setIrrSoilTemp(e.target.value)} className="form-input" id="irr-soil-temp" placeholder="24" />
              </label>
              <label className="field-label">
                {language === "te" ? "తేమ శాతం (% - సెన్సార్)" : "Humidity (% - Optional)"}
                <input type="number" min="0" max="100" value={irrHumidity} onChange={(e) => setIrrHumidity(e.target.value)} className="form-input" id="irr-humidity" placeholder="60" />
              </label>
              <label className="field-label">
                {language === "te" ? "పొలం విస్తీర్ణం (ఎకరాలు)" : "Farm Area (Acres)"}
                <input type="number" min="0.1" max="1000" step="0.5" value={irrAreaAcres} onChange={(e) => setIrrAreaAcres(e.target.value)} className="form-input" id="irr-area-acres" />
              </label>
            </div>
            <div style={{ marginTop: 10, display: "flex", alignItems: "center", gap: 8, fontSize: "0.82rem", color: "var(--text-secondary)" }}>
              <input type="checkbox" id="force-det" checked={irrForceDeterministic} onChange={(e) => setIrrForceDeterministic(e.target.checked)} style={{ cursor: "pointer" }} />
              <label htmlFor="force-det" style={{ cursor: "pointer" }}>
                {language === "te" ? "ICAR సాంప్రదాయ పద్ధతి మాత్రమే అమలు చేయండి (RL లేకుండా)" : "Enforce ICAR deterministic fallback (bypass RL policy)"}
              </label>
            </div>

            <div style={{ marginTop: 16, display: "flex", gap: 12 }}>
              <button className="btn-next" onClick={handleIrrigationCalc} disabled={irrLoading} type="button">
                <DropletIcon size={15} />
                <span>{irrLoading ? (language === "te" ? "లెక్కిస్తోంది..." : "Calculating...") : (language === "te" ? "నీటి బడ్జెట్ లెక్కించండి" : "Calculate Water Budget")}</span>
              </button>
            </div>

            {irrError && (
              <div style={{ marginTop: 12, padding: "10px 14px", background: "var(--red-bg)", borderRadius: "var(--r-md)", fontSize: "0.82rem", color: "var(--red-text)" }}>
                {irrError}
              </div>
            )}

            {irrResult && (
              <div style={{ marginTop: 20 }}>
                {/* Method identification badge */}
                <div style={{ marginBottom: 14, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  {irrResult.method_used === "ppo_reinforcement_learning" ? (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 10px", background: "var(--green-100)", color: "var(--green-900)", border: "1px solid var(--green-300)", borderRadius: 6, fontSize: "0.78rem", fontWeight: 600 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--green-600)" }}></span>
                      {language === "te" ? "PPO రీఇన్‌ఫోర్స్‌మెంట్ లెర్నింగ్ ఏజెంట్" : "PPO Reinforcement Learning Policy (Agent v1.0)"}
                      {irrResult.policy_confidence != null && ` • ${(irrResult.policy_confidence * 100).toFixed(1)}% policy preference`}
                    </span>
                  ) : (
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 10px", background: "var(--sky-100)", color: "var(--sky-900)", border: "1px solid var(--sky-300)", borderRadius: 6, fontSize: "0.78rem", fontWeight: 600 }}>
                      <span style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--sky-600)" }}></span>
                      {language === "te" ? "ICAR / ANGRAU సాంప్రదాయ పద్ధతి (Fallback)" : "ICAR / ANGRAU Deterministic Fallback"}
                    </span>
                  )}
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    Model Status: <strong style={{ color: irrResult.model_status === "READY" ? "var(--green-800)" : "var(--amber-800)" }}>{irrResult.model_status || "READY"}</strong>
                  </span>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 14 }}>
                  <div className="stat-highlight-card">
                    <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                      {language === "te" ? "పెరుగుదల దశ" : "Growth Stage"}
                    </span>
                    <div className="stat-highlight-val" style={{ fontSize: "1.1rem" }}>{irrResult.growth_stage}</div>
                  </div>
                  <div className="stat-highlight-card">
                    <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                      {language === "te" ? "నీటి లోతు" : "Water Depth"}
                    </span>
                    <div className="stat-highlight-val">{irrResult.recommended_water_depth_mm}<span style={{ fontSize: "0.8rem", fontWeight: 400 }}> mm</span></div>
                  </div>
                  <div className="stat-highlight-card">
                    <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                      {language === "te" ? "నికర నీరు (Net)" : "Net Farm Water"}
                    </span>
                    <div className="stat-highlight-val" style={{ fontSize: "1.1rem" }}>{(irrResult.total_farm_liters / 1000).toFixed(1)}<span style={{ fontSize: "0.8rem", fontWeight: 400 }}> KL</span></div>
                    <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>{irrResult.total_farm_liters.toLocaleString()} L ({irrResult.area_acres} ac)</span>
                  </div>
                  <div className="stat-highlight-card">
                    <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                      {language === "te" ? "స్థూల నీరు (Gross)" : "Gross Farm Water"}
                    </span>
                    <div className="stat-highlight-val" style={{ fontSize: "1.1rem" }}>{irrResult.gross_farm_liters ? (irrResult.gross_farm_liters / 1000).toFixed(1) : (irrResult.total_farm_liters / 1000).toFixed(1)}<span style={{ fontSize: "0.8rem", fontWeight: 400 }}> KL</span></div>
                    <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>{irrResult.application_efficiency_pct ? `${irrResult.application_efficiency_pct}% eff` : "Net volume"}</span>
                  </div>
                  <div className="stat-highlight-card">
                    <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                      {language === "te" ? "తదుపరి సేద్యం" : "Schedule"}
                    </span>
                    <div className="stat-highlight-val" style={{ fontSize: "1.1rem" }}>{language === "te" ? `ప్రతి ${irrResult.schedule_interval_days} రోజులు` : `Every ${irrResult.schedule_interval_days} days`}</div>
                  </div>
                </div>

                <div style={{ marginTop: 16, padding: 16, background: "var(--green-50)", borderRadius: "var(--r-md)", border: "1px solid var(--green-200)" }}>
                  <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--green-900)" }}>
                    {language === "te" ? irrResult.action_te : irrResult.action}
                  </div>
                  <p style={{ marginTop: 6, fontSize: "0.82rem", color: "var(--text-primary)", lineHeight: 1.55 }}>
                    {irrResult.reason}
                  </p>
                  <div style={{ marginTop: 8, display: "flex", gap: 16, fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                    <span>{language === "te" ? irrResult.recommended_method_te : irrResult.recommended_method}</span>
                    <span>•</span>
                    <span>{irrResult.liters_per_acre.toLocaleString()} L/acre (Net) • {irrResult.area_acres} acres</span>
                  </div>
                </div>

                <div style={{ marginTop: 12, padding: "10px 14px", background: "var(--amber-bg)", borderRadius: "var(--r-md)", fontSize: "0.75rem", color: "var(--amber-text)", display: "flex", gap: 8 }}>
                  <InfoIcon size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                  <div>
                    <div><strong>{language === "te" ? "మోడల్ గమనిక:" : "Model Diagnostics:"}</strong> {irrResult.rl_status_note}</div>
                    {irrResult.limitations && (
                      <div style={{ marginTop: 4, fontSize: "0.72rem", opacity: 0.9 }}>
                        <strong>{language === "te" ? "వ్యవసాయ నిబంధన:" : "Agronomic Disclaimer:"}</strong> {irrResult.limitations}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

    /* ══════════════════════════════════════════════════════════
     PLANNED MODULE VIEW (Market & Disease)
  ══════════════════════════════════════════════════════════ */
  /* ══════════════════════════════════════════════════════════
     MARKET INSIGHTS VIEW (Genuine APMC Forecast)
  ══════════════════════════════════════════════════════════ */
  function MarketView() {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 900 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><TrendingUpIcon size={18} /></span>
              {language === "te" ? "APMC మార్కెట్ ధర అంచనా" : "APMC Market Price Forecast"}
            </span>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontStyle: "italic" }}>
              Verified observation anchor + LightGBM seasonal model
            </span>
          </div>
          <div className="card-body">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
              <label className="field-label">
                {language === "te" ? "వ్యవసాయ ఉత్పత్తి" : "Commodity"}
                <select value={mktCommodity} onChange={(e) => setMktCommodity(e.target.value)} className="form-select" id="mkt-commodity">
                  {(marketCatalog?.popular_commodities || DEFAULT_POPULAR_COMMODITIES).map((c) => (
                    <option key={c.name} value={c.name}>
                      {language === "te" ? `${c.name_te} (${c.name})` : `${c.name} (${c.name_te})`}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-label">
                {language === "te" ? "మండీ" : "APMC Mandi"}
                <select value={mktMandi} onChange={(e) => setMktMandi(e.target.value)} className="form-select" id="mkt-mandi">
                  {marketMandiOptions.map((m) => (
                    <option key={m.name} value={m.name}>
                      {m.name} ({m.district}, {m.state})
                    </option>
                  ))}
                </select>
                {marketCatalog && verifiedMandisForCommodity.length === 0 && (
                  <small style={{ color: "var(--amber-text)", display: "block", marginTop: 4 }}>
                    {language === "te" ? "ఈ ఉత్పత్తికి ధృవీకరించిన స్థానిక పరిశీలన లేదు. వేరే ఉత్పత్తిని ఎంచుకోండి లేదా తాజా AGMARKNET డేటా కోసం మళ్లీ ప్రయత్నించండి." : "No verified local observation is currently available for this commodity. Choose another commodity or retry when AGMARKNET data is available."}
                  </small>
                )}
              </label>
              <label className="field-label">
                {language === "te" ? "రోజుల ముందుచూపు" : "Forecast Horizon (days)"}
                <input type="number" min="1" max="90" value={mktDaysAhead} onChange={(e) => setMktDaysAhead(e.target.value)} className="form-input" id="mkt-days" />
              </label>
            </div>
            <div style={{ marginTop: 16 }}>
              <button className="btn-next" onClick={handleMarketForecast} disabled={mktLoading} type="button">
                <TrendingUpIcon size={15} />
                <span>{mktLoading ? (language === "te" ? "అంచనా వేస్తోంది..." : "Forecasting...") : (language === "te" ? "ధర అంచనా వేయండి" : "Run Price Forecast")}</span>
              </button>
            </div>
            {mktError && (
              <div style={{ marginTop: 12, padding: "10px 14px", background: "var(--red-bg)", borderRadius: "var(--r-md)", fontSize: "0.82rem", color: "var(--red-text)" }}>
                {mktError}
              </div>
            )}
            {mktResult && (
              <div style={{ marginTop: 20 }}>
                {/* Provenance and Live Status Badge */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 12 }}>
                  {mktResult.live_feed_status === "live_agmarknet" && (
                    <span style={{ fontSize: "0.72rem", fontWeight: 700, padding: "3px 8px", borderRadius: 4, background: "#d1fae5", color: "#065f46", border: "1px solid #10b981" }}>
                      🟢 VERIFIED LIVE (AGMARKNET Official Feed)
                    </span>
                  )}
                  {mktResult.live_feed_status === "cached_observation" && (
                    <span style={{ fontSize: "0.72rem", fontWeight: 700, padding: "3px 8px", borderRadius: 4, background: "#fef3c7", color: "#92400e", border: "1px solid #f59e0b" }}>
                      🟡 VERIFIED CACHED (Local Mandi Store)
                    </span>
                  )}
                  {mktResult.live_feed_status === "offline_verified_benchmark" && (
                    <span style={{ fontSize: "0.72rem", fontWeight: 700, padding: "3px 8px", borderRadius: 4, background: "#e0e7ff", color: "#3730a3", border: "1px solid #6366f1" }}>
                      🔵 VERIFIED HISTORICAL BENCHMARK (DMI / AGMARKNET)
                    </span>
                  )}
                  <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                    Arrival Date: <strong>{mktResult.observation_date}</strong>
                  </span>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14 }}>
                  <div className="stat-highlight-card" style={{ borderLeft: "4px solid #4f46e5" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                      <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                        {language === "te" ? "అంచనా ధర" : "Forecast Price"}
                      </span>
                      <span style={{ fontSize: "0.65rem", fontWeight: 700, padding: "2px 6px", borderRadius: 4, background: "#e0e7ff", color: "#3730a3" }}>
                        PREDICTED
                      </span>
                    </div>
                    <div className="stat-highlight-val">₹{Math.round(mktResult.forecast_modal_price)}<span style={{ fontSize: "0.75rem", fontWeight: 400 }}> /{mktResult.unit}</span></div>
                    <div className="stat-highlight-sub">{mktResult.forecast_date} (Horizon: {mktDaysAhead}d)</div>
                  </div>
                  <div className="stat-highlight-card" style={{ borderLeft: "4px solid #059669" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                      <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                        {language === "te" ? "మార్కెట్ పరిశీలన" : "Market Observation"}
                      </span>
                      <span style={{ fontSize: "0.65rem", fontWeight: 700, padding: "2px 6px", borderRadius: 4, background: "#d1fae5", color: "#065f46" }}>
                        OBSERVED
                      </span>
                    </div>
                    <div className="stat-highlight-val" style={{ fontSize: "1.3rem" }}>₹{Math.round(mktResult.observed_market_price)}</div>
                    <div className="stat-highlight-sub">{mktResult.observation_timestamp} ({mktResult.mandi} APMC)</div>
                  </div>
                  <div className="stat-highlight-card" style={{ borderLeft: "4px solid #d97706" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                      <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                        {language === "te" ? "ధృవీకరించిన యాంకర్" : "Verified Anchor"}
                      </span>
                      <span style={{ fontSize: "0.65rem", fontWeight: 700, padding: "2px 6px", borderRadius: 4, background: "#fef3c7", color: "#92400e" }}>
                        BASELINE
                      </span>
                    </div>
                    <div className="stat-highlight-val" style={{ fontSize: "1.3rem" }}>₹{Math.round(mktResult.trend_component)}</div>
                    <div className="stat-highlight-sub">Actual latest observation used</div>
                  </div>
                  <div className="stat-highlight-card" style={{ borderLeft: "4px solid #6b7280" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                      <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                        {language === "te" ? "అంచనా మార్పు" : "Forecast Delta"}
                      </span>
                      <span style={{ fontSize: "0.65rem", fontWeight: 700, padding: "2px 6px", borderRadius: 4, background: "#f3f4f6", color: "#4b5563" }}>
                        RESIDUAL
                      </span>
                    </div>
                    <div className="stat-highlight-val" style={{ fontSize: "1.3rem" }}>{mktResult.residual_adjustment >= 0 ? "+" : ""}{mktResult.residual_adjustment.toFixed(1)}</div>
                    <div className="stat-highlight-sub">Final forecast minus anchor</div>
                  </div>
                </div>
                {mktResult.confidence_band && (
                  <div style={{ marginTop: 14, padding: 14, background: "var(--blue-bg)", borderRadius: "var(--r-md)", display: "flex", gap: 20, fontSize: "0.82rem", color: "var(--blue-text)" }}>
                    <span><strong>{language === "te" ? "తక్కువ:" : "Lower:"}</strong> ₹{Math.round(mktResult.confidence_band.lower_95 ?? mktResult.confidence_band.lower)}</span>
                    <span><strong>{language === "te" ? "ఎక్కువ:" : "Upper:"}</strong> ₹{Math.round(mktResult.confidence_band.upper_95 ?? mktResult.confidence_band.upper)}</span>
                    <span style={{ opacity: 0.7 }}>(95% CI)</span>
                  </div>
                )}
                {mktResult.seasonal_model_estimate && (
                  <div style={{ marginTop: 12, padding: "10px 14px", background: "var(--card-subtle)", borderRadius: "var(--r-md)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 6 }}>
                      <span><strong>LightGBM 500-Tree Seasonal Estimate:</strong> ₹{Math.round(mktResult.seasonal_model_estimate)} /{mktResult.unit}</span>
                      <span style={{ color: "var(--text-muted)" }}>Seasonal Drift: {mktResult.seasonal_difference >= 0 ? "+" : ""}₹{mktResult.seasonal_difference?.toFixed(1)}/Q ({mktResult.seasonal_trend_direction})</span>
                    </div>
                    <div style={{ marginTop: 4, color: "var(--text-muted)", fontSize: "0.72rem", lineHeight: 1.4 }}>
                      {mktResult.forecast_method_rationale}
                    </div>
                  </div>
                )}
                {mktResult.adapter_note && (
                  <div style={{ marginTop: 6, fontSize: "0.72rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                    ℹ️ {mktResult.adapter_note}
                  </div>
                )}
                <div style={{ marginTop: 10, fontSize: "0.75rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                  <strong>{language === "te" ? "ఎంపిక:" : "Selection:"}</strong> {mktResult.commodity} · {mktResult.mandi} ({mktResult.state}, {mktResult.district})<br />
                  <strong>{language === "te" ? "పద్ధతి:" : "Method:"}</strong> {mktResult.forecast_method_label} · <strong>{language === "te" ? "మూలం:" : "Source:"}</strong> {mktResult.data_source}
                </div>
                <div style={{ marginTop: 8, padding: "10px 14px", background: "var(--amber-bg)", borderRadius: "var(--r-md)", fontSize: "0.75rem", color: "var(--amber-text)", display: "flex", gap: 8 }}>
                  <InfoIcon size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                  <span>{mktResult.limitations}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════
     PLANT DISEASE & INTELLIGENCE INTEGRATED VIEW
     (ResNet50 + SAM + LIME + BLIP)
  ══════════════════════════════════════════════════════════ */
  function DiseaseView() {
    const executed = plantAnalysis?.executed_models || {};
    const classifier = executed.disease_classifier?.result || diseaseResult;
    const sam = executed.sam?.result;
    const lime = executed.lime?.result;
    const blip = executed.blip?.result;

    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 24, maxWidth: 1040, width: "100%" }}>
        {/* Upload & Workspace Card */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              <span className="card-title-icon"><BugIcon size={18} /></span>
              {language === "te"
                ? "మొక్కల తెగుళ్ల సమగ్ర పరిశోధనా కేంద్రం — ResNet50, SAM, LIME & BLIP"
                : "Plant Disease & Intelligence Workspace — ResNet50, SAM, LIME & BLIP"}
            </span>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontStyle: "italic" }}>
              Integrated Research Pipeline · Same Original Upload
            </span>
          </div>

          <div className="card-body">
            {/* Upload Zone */}
            <div style={{ padding: 20, background: "var(--page-bg)", borderRadius: "var(--r-md)", border: "2px dashed var(--border)", textAlign: "center" }}>
              <label htmlFor="disease-photo-input" style={{ cursor: "pointer", display: "block" }}>
                <input
                  id="disease-photo-input"
                  type="file"
                  accept=".jpg,.jpeg,.png,.webp"
                  style={{ display: "none" }}
                  onChange={handleDiseaseFileSelect}
                />
                <div style={{ color: "var(--green-600)", marginBottom: 8 }}><ImageIcon size={36} /></div>
                <div style={{ fontWeight: 600, fontSize: "0.98rem", color: "var(--green-950)" }}>
                  {language === "te" ? "ఆకు / పంట ఫోటోను అప్‌లోడ్ చేయండి" : "Upload Crop Leaf Photo for Complete Analysis"}
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}>
                  JPEG, PNG, WEBP · {language === "te" ? "గరిష్టం 10MB · ఒకే చిత్రంతో అన్ని మోడళ్ల విశ్లేషణ" : "Max 10 MB · Evaluated simultaneously across all vision models"}
                </div>
              </label>
            </div>

            {/* Preview & Action Button */}
            {diseasePreviewUrl && (
              <div style={{ marginTop: 16, display: "flex", gap: 20, flexWrap: "wrap", alignItems: "center" }}>
                <div style={{ width: 140, height: 140, borderRadius: 10, overflow: "hidden", border: "2px solid var(--border)", flexShrink: 0 }}>
                  <img src={diseasePreviewUrl} alt="Leaf preview" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
                <div style={{ flex: 1, minWidth: 240 }}>
                  <div style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-primary)" }}>
                    {diseaseFile?.name} ({(diseaseFile ? diseaseFile.size / 1024 : 0).toFixed(0)} KB)
                  </div>
                  <p style={{ margin: "4px 0 12px 0", fontSize: "0.78rem", color: "var(--text-secondary)" }}>
                    Original image is preserved and dispatched to ResNet50 (Classification), SAM (Segmentation), LIME (Explainability), and BLIP (Detailed Description).
                  </p>
                  <button
                    className="btn-next"
                    onClick={handleDiseaseScreening}
                    disabled={diseaseLoading}
                    type="button"
                    style={{ padding: "10px 20px", fontSize: "0.9rem", fontWeight: 600, display: "inline-flex", alignItems: "center", gap: 8 }}
                  >
                    <SparklesIcon size={16} />
                    <span>
                      {diseaseLoading
                        ? (language === "te" ? "సమగ్ర విశ్లేషణ నడుస్తోంది..." : "Running Complete Plant Analysis…")
                        : (language === "te" ? "పూర్తి విశ్లేషణ చేయండి (అన్ని మోడళ్లు)" : "Run Complete Plant Analysis (All Models)")}
                    </span>
                  </button>
                </div>
              </div>
            )}

            {diseaseError && (
              <div style={{ marginTop: 14, padding: "12px 16px", background: "var(--red-bg)", borderRadius: "var(--r-md)", fontSize: "0.82rem", color: "var(--red-text)" }}>
                <strong>Execution Note:</strong> {diseaseError}
              </div>
            )}

            {/* Model Readiness Row */}
            <div style={{ marginTop: 20 }}>
              <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                Research Model Readiness
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))", gap: 8 }}>
                {[
                  { name: "ResNet50 Vision", key: "disease_classifier", desc: "23-Class foliar classifier" },
                  { name: "SAM ViT-B", key: "sam", desc: "Instance segmentation" },
                  { name: "LIME Explainer", key: "lime", desc: "Superpixel influence" },
                  { name: "BLIP Captioner", key: "blip", desc: "Vision-language captioning" },
                ].map((m) => {
                  const run = executed[m.key];
                  // Priority: actual run status > API model availability status > READY
                  const apiStatus = plantModelStatus.find((p) => p.model === m.key)?.status;
                  const st = run?.status && run.status !== "NOT_RUN" ? run.status : (apiStatus || "CHECKING");
                  const isProcessing = st === "PROCESSING";
                  return (
                    <div key={m.key} style={{ padding: "8px 12px", background: "var(--page-bg)", borderRadius: 8, border: `1px solid ${isProcessing ? "#fbbf24" : "var(--border)"}`, transition: "border-color 0.3s" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "0.8rem", fontWeight: 600 }}>{m.name}</span>
                        <span className={`status-chip ${String(st).toLowerCase()}`}>{st}</span>
                      </div>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>
                        {run?.execution_time_sec ? `${run.execution_time_sec}s runtime` : m.desc}
                      </div>
                      {isProcessing && (
                        <div style={{ marginTop: 4, height: 2, background: "#e5e7eb", borderRadius: 1, overflow: "hidden" }}>
                          <div style={{ height: "100%", background: "#f59e0b", width: "60%", animation: "slide-progress 1.5s ease-in-out infinite" }} />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* RESULTS SECTION: Shown once analysis completes */}
        {plantAnalysis && (
          <>
            {/* Integrated 4-Panel Research Visualization (Notebook Cell 15 Output) */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  <span className="card-title-icon"><ImageIcon size={18} /></span>
                  Integrated 4-Panel Research Visualization (Notebook Output)
                </span>
                <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
                  Multi-Model Foliar Analysis · ResNet50, SAM, LIME &amp; BLIP
                </span>
              </div>
              <div className="card-body">
                <p style={{ margin: "0 0 12px 0", fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                  Direct reproduction of the integrated multi-model research figure combining:
                  <strong> Original Leaf</strong>, <strong>SAM2/SAM Segmentation Overlay</strong>, <strong>BLIP Image Understanding</strong>, and <strong>LIME Superpixel Explanation</strong>.
                </p>
                <div style={{ borderRadius: 12, overflow: "hidden", border: "2px solid var(--border)", background: "#000", textAlign: "center" }}>
                  <img
                    src={`${apiUrl}/api/plant-intelligence/${plantAnalysis.analysis_id}/assets/integrated_plant_disease_results.png`}
                    alt="Integrated Plant Disease Analysis Using ResNet50, SAM, BLIP and LIME"
                    style={{ width: "100%", maxHeight: 680, objectFit: "contain", display: "block" }}
                    onError={(e) => {
                      (e.currentTarget as HTMLElement).style.display = "none";
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Diagnostic Findings & Prescription Banner */}
            {classifier && (
              <div className="card">
                <div className="card-header">
                  <span className="card-title">
                    <span className="card-title-icon"><BugIcon size={18} /></span>
                    ResNet50 Vision Classifier Diagnosis
                  </span>
                  <span className="status-chip ready">CONFIRMED INFERENCE</span>
                </div>
                <div className="card-body">
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
                    <div className="stat-highlight-card" style={{ background: classifier.is_healthy ? "var(--green-50)" : "var(--red-bg)", border: classifier.is_healthy ? "1px solid var(--green-200)" : "1px solid #f5c6c6" }}>
                      <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                        {language === "te" ? "రోగ నిర్ధారణ" : "Identified Crop Disease"}
                      </span>
                      <div style={{ fontSize: "1.2rem", fontWeight: 700, color: classifier.is_healthy ? "var(--green-800)" : "var(--red-text)", marginTop: 4 }}>
                        {classifier.predicted_class?.replace(/_/g, " ")}
                      </div>
                      <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: 2 }}>
                        {classifier.label_te}
                      </div>
                    </div>
                    <div className="stat-highlight-card">
                      <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
                        {language === "te" ? "విశ్వసనీయత" : "Softmax Confidence"}
                      </span>
                      <div className="stat-highlight-val">{classifier.confidence_pct?.toFixed(1)}<span style={{ fontSize: "0.8rem", fontWeight: 400 }}>%</span></div>
                      <div className="confidence-meter">
                        <div className="confidence-meter-fill" style={{ width: `${Math.min(100, classifier.confidence_pct || 0)}%` }} />
                      </div>
                    </div>
                  </div>

                  {/* ICAR Mitigation */}
                  <div style={{ marginTop: 16, padding: 16, background: "var(--green-50)", borderRadius: "var(--r-md)", border: "1px solid var(--green-200)" }}>
                    <div style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--green-900)" }}>
                      {language === "te" ? "ICAR సిఫార్సు చేసిన నివారణ చర్యలు" : "ICAR Recommended Agronomic Action"}
                    </div>
                    <p style={{ marginTop: 6, fontSize: "0.85rem", color: "var(--text-primary)", lineHeight: 1.55 }}>
                      {classifier.recommended_mitigation || classifier.actionable_recommendations}
                    </p>
                  </div>

                  {/* Top Candidate Distribution */}
                  {classifier.top_candidates && classifier.top_candidates.length > 1 && (
                    <div style={{ marginTop: 16 }}>
                      <div style={{ fontWeight: 600, fontSize: "0.82rem", color: "var(--green-950)", marginBottom: 8 }}>
                        Top Candidate Class Probabilities (ResNet50 Softmax Distribution)
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        {classifier.top_candidates.slice(0, 5).map((c: any, i: number) => {
                          const rawConf = Number(c.confidence) || 0;
                          const confPct = rawConf > 1 ? Math.min(100, rawConf) : Math.min(100, rawConf * 100);
                          return (
                            <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 12px", background: "var(--page-bg)", borderRadius: 6, fontSize: "0.8rem" }}>
                              <span style={{ fontWeight: 500 }}>{c.class_name?.replace(/_/g, " ")} ({c.label_te})</span>
                              <div style={{ display: "flex", alignItems: "center", gap: 10, width: 140 }}>
                                <div style={{ flex: 1, height: 6, background: "var(--border)", borderRadius: 3, overflow: "hidden" }}>
                                  <div style={{ height: "100%", width: `${Math.min(100, confPct).toFixed(0)}%`, background: i === 0 ? "var(--green-600)" : "var(--text-muted)" }} />
                                </div>
                                <span style={{ fontWeight: 600, minWidth: 40, textAlign: "right", color: i === 0 ? "var(--green-800)" : "var(--text-secondary)" }}>
                                  {confPct.toFixed(1)}%
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* SAM & LIME Individual Model Breakdown Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(460px, 1fr))", gap: 20 }}>
              {/* SAM Card */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">
                    <span className="card-title-icon">📐</span>
                    SAM (Segment Anything) Zero-Shot Segmentation — Image + Text
                  </span>
                  <span className={`status-chip ${executed.sam?.status?.toLowerCase() || "ready"}`}>
                    {executed.sam?.status || "READY"}
                  </span>
                </div>
                <div className="card-body">
                  <p style={{ margin: "0 0 10px 0", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    Zero-shot instance segmentation isolating vegetative foliar canopy from ambient noise.
                  </p>
                  {sam ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: "0.78rem", background: "var(--page-bg)", padding: 10, borderRadius: 8 }}>
                        <span>Masks: <strong>{sam.mask_count}</strong></span>
                        <span>Canopy Coverage: <strong>{sam.leaf_coverage_pct}%</strong></span>
                        <span>Total Pixels: <strong>{sam.total_segmented_pixels?.toLocaleString()}</strong></span>
                      </div>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                        <div>
                          <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Jet Colormap Overlay (Notebook Style)</span>
                          <img
                            src={`${apiUrl}/api/plant-intelligence/${plantAnalysis.analysis_id}/assets/sam-overlay.png`}
                            alt="SAM Overlay"
                            onError={(e) => {
                              const target = e.currentTarget as HTMLImageElement;
                              if (!target.dataset.fallback) {
                                target.dataset.fallback = "1";
                                target.src = `${apiUrl}/api/plant-intelligence/${plantAnalysis.analysis_id}/assets/original.jpg`;
                              }
                            }}
                            style={{ width: "100%", borderRadius: 8, border: "1px solid var(--border)" }}
                          />
                        </div>
                        <div>
                          <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Foliar Cutout</span>
                          <img
                            src={`${apiUrl}/api/plant-intelligence/${plantAnalysis.analysis_id}/assets/sam-segmented.png`}
                            alt="SAM Cutout"
                            onError={(e) => {
                              const target = e.currentTarget as HTMLImageElement;
                              if (!target.dataset.fallback) {
                                target.dataset.fallback = "1";
                                target.src = `${apiUrl}/api/plant-intelligence/${plantAnalysis.analysis_id}/assets/original.jpg`;
                              }
                            }}
                            style={{ width: "100%", borderRadius: 8, border: "1px solid var(--border)" }}
                          />
                        </div>
                      </div>
                      <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.45 }}>{sam.summary}</p>
                    </div>
                  ) : executed.sam?.status === "PROCESSING" ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      <div style={{ height: 160, background: "linear-gradient(90deg,#f0f4f1 25%,#e8f0ea 50%,#f0f4f1 75%)", backgroundSize: "400% 100%", borderRadius: 8, animation: "shimmer 1.5s infinite" }} />
                      <div style={{ fontSize: "0.8rem", color: "#92400e", fontWeight: 600 }}>⏳ SAM segmentation running in background…</div>
                    </div>
                  ) : (
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {executed.sam?.error ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                          <span style={{ color: "#991b1b", lineHeight: 1.45 }}>⚠ {executed.sam.error}</span>
                          <div>
                            <button
                              type="button"
                              className="btn-next"
                              onClick={() => handleRunSingleModel(plantAnalysis.analysis_id, "sam")}
                              disabled={diseaseLoading}
                              style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "6px 14px", fontSize: "0.78rem" }}
                            >
                              <SparklesIcon size={14} />
                              <span>{diseaseLoading ? "Running SAM…" : "Retry SAM ViT-B Segmentation"}</span>
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                          <span>Awaiting segmentation output.</span>
                          {plantAnalysis?.analysis_id && (
                            <button
                              type="button"
                              className="btn-next"
                              onClick={() => handleRunSingleModel(plantAnalysis.analysis_id, "sam")}
                              disabled={diseaseLoading}
                              style={{ padding: "5px 12px", fontSize: "0.75rem" }}
                            >
                              Run SAM ViT-B
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* LIME Card */}
              <div className="card">
                <div className="card-header">
                  <span className="card-title">
                    <span className="card-title-icon">🔍</span>
                    LIME (Explainability & Lesion Superpixels) — Image + Text
                  </span>
                  <span className={`status-chip ${executed.lime?.status?.toLowerCase() || "ready"}`}>
                    {executed.lime?.status || "READY"}
                  </span>
                </div>
                <div className="card-body">
                  <p style={{ margin: "0 0 10px 0", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                    Perturbs 150 local superpixels to calculate boundaries that drove the ResNet50 diagnosis.
                  </p>
                  {lime ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                      <div style={{ fontSize: "0.78rem", background: "var(--page-bg)", padding: 10, borderRadius: 8 }}>
                        Explained Target: <strong>{lime.explained_class}</strong> · Features Analyzed: <strong>{lime.features_analyzed}</strong>
                      </div>
                      <div>
                        <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>Marked Superpixel Boundaries</span>
                        <img
                          src={`${apiUrl}/api/plant-intelligence/${plantAnalysis.analysis_id}/assets/lime-explanation.png`}
                          alt="LIME Explanation"
                          onError={(e) => {
                            const target = e.currentTarget as HTMLImageElement;
                            if (!target.dataset.fallback) {
                              target.dataset.fallback = "1";
                              target.src = `${apiUrl}/api/plant-intelligence/${plantAnalysis.analysis_id}/assets/original.jpg`;
                            }
                          }}
                          style={{ width: "100%", borderRadius: 8, border: "1px solid var(--border)" }}
                        />
                      </div>
                      <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.45 }}>
                        {lime.interpretation}
                      </p>
                    </div>
                  ) : executed.lime?.status === "PROCESSING" ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      <div style={{ height: 160, background: "linear-gradient(90deg,#f0f4f1 25%,#e8f0ea 50%,#f0f4f1 75%)", backgroundSize: "400% 100%", borderRadius: 8, animation: "shimmer 1.5s infinite" }} />
                      <div style={{ fontSize: "0.8rem", color: "#92400e", fontWeight: 600 }}>⏳ LIME superpixel analysis running in background…</div>
                    </div>
                  ) : (
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {executed.lime?.error ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                          <span style={{ color: "#991b1b", lineHeight: 1.45 }}>⚠ {executed.lime.error}</span>
                          <div>
                            <button
                              type="button"
                              className="btn-next"
                              onClick={() => handleRunSingleModel(plantAnalysis.analysis_id, "lime")}
                              disabled={diseaseLoading}
                              style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "6px 14px", fontSize: "0.78rem" }}
                            >
                              <SparklesIcon size={14} />
                              <span>{diseaseLoading ? "Running LIME…" : "Retry LIME Explanation"}</span>
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                          <span>Awaiting LIME explanation.</span>
                          {plantAnalysis?.analysis_id && (
                            <button
                              type="button"
                              className="btn-next"
                              onClick={() => handleRunSingleModel(plantAnalysis.analysis_id, "lime")}
                              disabled={diseaseLoading}
                              style={{ padding: "5px 12px", fontSize: "0.75rem" }}
                            >
                              Run LIME
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Dedicated BLIP Section: Detailed Plant Image Description (Image + Text) */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">
                  <span className="card-title-icon">💬</span>
                  Detailed Plant Image Description — Salesforce BLIP Vision (Image + Text)
                </span>
                <span className="status-chip ready">MULTIMODAL PERCEPTION</span>
              </div>
              <div className="card-body">
                <div style={{ padding: 18, background: "var(--page-bg)", borderRadius: 10, border: "1px solid var(--border)", display: "flex", flexDirection: "column", gap: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                    <div>
                      <strong style={{ fontSize: "0.95rem", color: "var(--green-950)" }}>Salesforce BLIP Foliar Scene Perception &amp; Description</strong>
                      <div style={{ fontSize: "0.74rem", color: "var(--text-muted)" }}>Model: Salesforce/blip-image-captioning-base · Conditional foliar feature grounding</div>
                    </div>
                    <span className={`status-chip ${executed.blip?.status?.toLowerCase() || "not_run"}`}>{executed.blip?.status || "NOT_RUN"}</span>
                  </div>

                  {blip ? (
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 18, alignItems: "start" }}>
                      {/* Visual Asset */}
                      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase" }}>Generated Observation Overlay:</span>
                        <img
                          src={`${apiUrl}/api/plant-intelligence/${plantAnalysis.analysis_id}/assets/blip-analysis.png`}
                          alt="BLIP Analysis"
                          onError={(e) => {
                            const target = e.currentTarget as HTMLImageElement;
                            if (!target.dataset.fallback) { target.dataset.fallback = "1"; target.src = `${apiUrl}/api/plant-intelligence/${plantAnalysis.analysis_id}/assets/original.jpg`; }
                          }}
                          style={{ width: "100%", maxHeight: 300, objectFit: "contain", borderRadius: 8, border: "1px solid var(--border)", background: "#ffffff" }}
                        />
                      </div>

                      {/* Natural Language Observations */}
                      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                        <div style={{ padding: 14, background: "white", borderRadius: 8, border: "1px solid var(--border)" }}>
                          <span style={{ fontSize: "0.72rem", color: "var(--green-800)", textTransform: "uppercase", fontWeight: 700, display: "block", marginBottom: 6 }}>
                            Detailed Foliar Observations:
                          </span>
                          <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--text-primary)", lineHeight: 1.6, fontWeight: 500 }}>
                            &quot;{blip.detailed_caption || blip.full_description || blip.caption}&quot;
                          </p>
                        </div>

                        {blip.caption && blip.detailed_caption && (
                          <div style={{ padding: 12, background: "var(--page-bg)", borderRadius: 8, border: "1px solid var(--border)" }}>
                            <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 600, display: "block", marginBottom: 4 }}>
                              Concise Caption Summary:
                            </span>
                            <p style={{ margin: 0, fontSize: "0.82rem", color: "var(--text-secondary)", fontStyle: "italic" }}>
                              &quot;{blip.caption}&quot;
                            </p>
                          </div>
                        )}

                        <div style={{ padding: "10px 12px", background: "#f0fdf4", borderRadius: 8, border: "1px solid #bbf7d0", fontSize: "0.76rem", color: "#166534", lineHeight: 1.45 }}>
                          <strong>Independent Foliar Perception:</strong> This visual description details observable physical leaf features (pigmentation, lesion patterns, edge integrity) independently generated by BLIP, complementing the ResNet50 taxonomic disease classification.
                        </div>
                      </div>
                    </div>
                  ) : executed.blip?.status === "PROCESSING" ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                      <div style={{ height: 160, background: "linear-gradient(90deg,#f0f4f1 25%,#e8f0ea 50%,#f0f4f1 75%)", backgroundSize: "400% 100%", borderRadius: 8, animation: "shimmer 1.5s infinite" }} />
                      <div style={{ fontSize: "0.8rem", color: "#92400e", fontWeight: 600 }}>⏳ BLIP foliar observations running in background…</div>
                    </div>
                  ) : (
                    <div style={{ fontSize: "0.82rem", color: "var(--text-muted)", padding: 12, background: "white", borderRadius: 8, border: "1px solid var(--border)" }}>
                      {executed.blip?.error ? <span style={{ color: "#991b1b" }}>⚠ {executed.blip.error}</span> : '"Awaiting BLIP detailed foliar observation generation."'}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Live Analysis Progress Banner */}
            {Object.values(executed).some((x: any) => x?.status === "PROCESSING") && (
              <div style={{ padding: "12px 16px", background: "#fefce8", borderRadius: 10, border: "1px solid #fde68a", display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 16, height: 16, borderRadius: "50%", border: "2px solid #f59e0b", borderTopColor: "transparent", animation: "spin 0.8s linear infinite", flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#78350f" }}>Models Running in Background</div>
                  <div style={{ fontSize: "0.75rem", color: "#92400e" }}>
                    {["sam", "lime", "blip"]
                      .filter((m) => executed[m]?.status === "PROCESSING")
                      .map((m) => m.toUpperCase())
                      .join(", ")} — Results will appear automatically every 4 seconds
                  </div>
                </div>
              </div>
            )}

            {/* Action Bar: PDF Report & Chatbot */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 14,
                padding: "16px 20px",
                background: "var(--green-50)",
                borderRadius: "var(--r-md)",
                border: "1px solid var(--green-200)",
              }}
            >
              <div>
                <strong style={{ fontSize: "0.9rem", color: "var(--green-950)", display: "block" }}>
                  Complete Multi-Model Analysis Persisted (Session ID: {plantAnalysis.analysis_id})
                </strong>
                <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                  {(() => {
                    const mkeys = ["disease_classifier", "sam", "lime", "blip"];
                    const done = mkeys.filter((mk) => executed[mk]?.status === "COMPLETED").length;
                    const proc = mkeys.filter((mk) => executed[mk]?.status === "PROCESSING").length;
                    return proc > 0
                      ? `${done}/4 Models Completed · ${proc} Still Running · Results Update Every 4s`
                      : `${done}/4 Models Completed · Visual Assets Created · Integrated into Rythu AI Floating Chatbot`;
                  })()}
                </span>
              </div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                {Object.values(executed).some((x: any) => x?.status === "NOT_RUN" || x?.status === "FAILED") && (
                  <button
                    type="button"
                    className="btn-next"
                    onClick={() => handleRunMissingModels(plantAnalysis.analysis_id)}
                    disabled={diseaseLoading}
                    style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "9px 16px", background: "#d97706" }}
                  >
                    <SparklesIcon size={15} />
                    <span>{diseaseLoading ? "Running Remaining Models…" : "Run Pending Models (SAM, LIME, BLIP)"}</span>
                  </button>
                )}
                <button
                  type="button"
                  className="btn-next"
                  onClick={() => handleDownloadPlantReport(plantAnalysis.analysis_id)}
                  disabled={plantReportLoading}
                  style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "9px 16px" }}
                >
                  <FileTextIcon size={15} />
                  <span>{plantReportLoading ? "Generating PDF…" : "Download Research PDF Report"}</span>
                </button>
                <button
                  type="button"
                  className="card-action-btn"
                  onClick={() => {
                    setChatOpen(true);
                    if (chatMinimized) setChatMinimized(false);
                    handleSendMessage("Explain what each model did for my plant image");
                  }}
                  style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "9px 16px" }}
                >
                  <BotIcon size={15} />
                  <span>Ask Rythu AI About This Leaf</span>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    );
  }

  function PlannedModuleView({
    title,
    icon,
    modelId,
    reason,
  }: {
    title: string;
    icon: React.ReactNode;
    modelId: string;
    reason: string;
  }) {
    return (
      <div className="card" style={{ maxWidth: 760 }}>
        <div className="card-header">
          <span className="card-title">
            <span className="card-title-icon">{icon}</span>
            {title}
          </span>
          <span className="status-chip blocked" style={{ textTransform: "uppercase" }}>
            Planned / Blocked in Audit
          </span>
        </div>
        <div className="card-body">
          <div style={{ display: "flex", gap: 14, alignItems: "flex-start", padding: 16, background: "var(--amber-bg)", borderRadius: "var(--r-md)", color: "var(--amber-text)" }}>
            <InfoIcon size={20} style={{ flexShrink: 0, marginTop: 2 }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: "0.92rem" }}>
                {language === "te" ? "మోడల్ ఆడిట్ స్థితి: నిలిపివేయబడింది" : `Model Registry Audit: [${modelId}]`}
              </div>
              <p style={{ marginTop: 6, fontSize: "0.85rem", lineHeight: 1.55 }}>
                {reason}
              </p>
            </div>
          </div>
          <div style={{ marginTop: 20, fontSize: "0.83rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
            {language === "te"
              ? "క్షేత్రIQ విశ్వసనీయత నిబంధన: రైతులకు తప్పుడు లేదా కల్పిత సమాచారం అందించడం ఖచ్చితంగా నివారించబడుతుంది. నమూనా డేటా పూర్తిగా ధృవీకరించబడిన తర్వాత మాత్రమే ఈ ఫీచర్లు అందుబాటులోకి వస్తాయి."
              : "Trust-First AI Standard: KshetraIQ strictly prohibits fabricating synthetic market prices or unverified plant disease diagnoses. Modules remain transparently unavailable until production runtime manifests and verified calibration datasets are deployed."}
          </div>

          {modelId === "plant-disease-v1" && (
            <div style={{ marginTop: 20 }}>
              <div style={{ fontWeight: 600, fontSize: "0.88rem", color: "var(--green-950)", marginBottom: 4 }}>
                {language === "te" ? "పంట రోగ నిర్ధారణ ఫోటో అప్‌లోడ్ (పరీక్షార్థం)" : "Crop Leaf Photo Upload (Staging & Diagnostics Ingestion)"}
              </div>
              <FileUploadBox
                category="crop_photo"
                title={t.uploadCropPhotoTitle}
                subtitle={t.uploadHint}
                accept=".jpg,.jpeg,.png,.webp"
                onUpload={handleFileUpload}
                uploading={uploadingCategory === "crop_photo"}
                files={uploadedFiles}
                onDelete={handleDeleteUpload}
                language={language}
              />
              {uploadError && uploadingCategory === "crop_photo" && (
                <div style={{ color: "var(--red-text)", fontSize: "0.75rem", marginTop: 4 }}>
                  {uploadError}
                </div>
              )}
              {uploadSuccessMsg && (
                <div style={{ color: "var(--green-700)", fontSize: "0.75rem", marginTop: 4 }}>
                  {uploadSuccessMsg}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════
     REPORTS VIEW
  ══════════════════════════════════════════════════════════ */
  function ReportsView() {
    return (
      <div className="card" style={{ maxWidth: 760 }}>
        <div className="card-header">
          <span className="card-title">
            <span className="card-title-icon"><FileTextIcon size={18} /></span>
            {language === "te" ? "రైతు నివేదికల కేంద్రం" : "Farm Assessment Reports Center"}
          </span>
          {result && (
            <button
              className="card-action-btn"
              onClick={openReportConfirmation}
            >
              {t.exportBtn}
            </button>
          )}
        </div>
        <div className="card-body">
          {result ? (
            <div>
              <div style={{ padding: 16, background: "var(--page-bg)", borderRadius: "var(--r-md)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 600, color: "var(--green-950)" }}>
                    KshetraIQ Dossier — {farmName}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 2 }}>
                    ID: {result.assessment_id.slice(0, 8)}… · Verified ReportLab Engine
                  </div>
                </div>
                <button
                  className="btn-next"
                  onClick={openReportConfirmation}
                >
                  <FileTextIcon size={14} />
                  <span>{language === "te" ? "PDF డౌన్‌లోడ్ చేయండి" : "Download Official PDF"}</span>
                </button>
              </div>
              <p style={{ marginTop: 14, fontSize: "0.8rem", color: "var(--text-muted)" }}>
                {language === "te"
                  ? "రెండు దశల ధృవీకరణ: నివేదికను రూపొందించడానికి ముందు ముందస్తు సమీక్ష అవసరం."
                  : "Two-step confirmed generation: Review key parameters in the confirmation dialog before compiling PDF bytes."}
              </p>
            </div>
          ) : (
            <div className="empty-state">
              <FileTextIcon size={28} />
              <div className="empty-title">
                {language === "te" ? "ఇంకా నివేదికలు తయారు కాలేదు" : "No Reports Generated Yet"}
              </div>
              <div className="empty-desc">
                {language === "te"
                  ? "అధికారిక తెలుగు / ఇంగ్లీష్ PDF నివేదికను పొందడానికి మొదట పొలం అంచనా పూర్తి చేయండి."
                  : "Complete a farm assessment to generate an official, two-step confirmed bilingual PDF dossier."}
              </div>
              <button
                className="btn-next"
                style={{ marginTop: 10 }}
                onClick={() => setView("assessment")}
              >
                <span>{t.runAssessmentBtn}</span>
                <ArrowRightIcon size={14} />
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════
     MODEL REGISTRY VIEW
  ══════════════════════════════════════════════════════════ */
  function RegistryView() {
    const verifiedCount = modelCatalog.filter(
      (m) =>
        (m.readiness_status ?? m.contract_status) === "VERIFIED" ||
        (m.readiness_status ?? m.contract_status) === "verified"
    ).length;

    return (
      <div className="card" style={{ maxWidth: 960 }}>
        <div className="card-header">
          <span className="card-title">
            <span className="card-title-icon"><DatabaseIcon size={18} /></span>
            {t.navModelRegistry}
          </span>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="card-action-btn" type="button" disabled={verifyingModels} onClick={() => refreshModelCatalog()}>
              {verifyingModels ? (language === "te" ? "ధృవీకరిస్తున్నా…" : "Verifying…") : (language === "te" ? "ధృవీకరణ" : "Run Verification")}
            </button>
            <span className="status-chip live">
              {verifiedCount}/{modelCatalog.length} {language === "te" ? "ధృవీకరించినవి" : "Verified"}
            </span>
          </div>
        </div>
        <div className="card-body">
          {modelCatalog.length > 0 ? (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                gap: 16,
                marginTop: 4,
              }}
            >
              {modelCatalog.map((m) => {
                const isVerified =
                  (m.readiness_status ?? m.contract_status) === "VERIFIED" ||
                  (m.readiness_status ?? m.contract_status) === "verified";
                const purpose = MODEL_PURPOSES[m.model_id];
                return (
                  <div key={m.model_id} className="model-verify-card">
                    <div className="model-card-header">
                      <span className="model-friendly-name">
                        {m.model_id
                          .replace(/-v\d+$/, "")
                          .replace(/-/g, " ")
                          .replace(/\b\w/g, (c) => c.toUpperCase())}
                      </span>
                      {isVerified && (
                        <span className="verified-badge">✓ VERIFIED</span>
                      )}
                    </div>
                    <div className="model-id-label">{m.model_id}</div>
                    {purpose && (
                      <div className="model-purpose">{purpose}</div>
                    )}
                    <details style={{ marginTop: 4 }}>
                      <summary
                        style={{
                          fontSize: "0.72rem",
                          color: "var(--text-muted)",
                          cursor: "pointer",
                          userSelect: "none",
                        }}
                      >
                        {language === "te" ? "వివరాలు చూపండి" : "Show details"}
                      </summary>
                      <div style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 4 }}>
                        <div className="registry-row-artifact">
                          <span>{language === "te" ? "ఆర్టిఫాక్టు:" : "Artifact:"}</span>{" "}
                          <code style={{ fontSize: "0.68rem" }}>{m.active_artifact ?? m.artifact}</code>
                        </div>
                        {m.last_verified_at && (
                          <div className="registry-row-artifact">
                            <span>Last verified:</span>{" "}
                            {new Date(m.last_verified_at).toLocaleString()}
                          </div>
                        )}
                        {m.runtime_verification_result && (
                          <div className="registry-row-artifact">
                            <span>Runtime:</span> {m.runtime_verification_result}
                          </div>
                        )}
                        {m.model_type && (
                          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                            {m.model_type}
                          </div>
                        )}
                      </div>
                    </details>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-desc">{language === "te" ? "\u092e\u1c4b\u1c38\u1c41\u200c\u0020\u1c38\u1c48\u1c30\u1c38\u1c38\u1c4b\u200c\u0020\u1c38\u1c4b\u1c38\u1c38\u1c41\u200c\u0020\u0905\u1c35\u1c41\u1c4d\u1c41\u1c4d\u1c41\u2026" : "Loading model catalog\u2026"}</div>
            </div>
          )}

          <div
            style={{
              marginTop: 20,
              padding: "10px 14px",
              background: "var(--green-50)",
              borderRadius: "var(--r-md)",
              borderLeft: "3px solid var(--green-600)",
              fontSize: "0.75rem",
              color: "var(--text-secondary)",
              lineHeight: 1.5,
            }}
          >
            <strong>{"🔬 "}{" "}
              {language === "te" ? "KshetraIQ ML ఆర్కిటేక్చరు:" : "KshetraIQ ML Architecture:"}
            </strong>{"\xa0"}
            {language === "te"
              ? "అన్ని 8 మాడల్సు ధృవీకరించలేదీ. Crop Recommendation కోసం Random Forest, Market Pricing కోసం LightGBM + Persistence Hybrid, Irrigation కోసం PPO Reinforcement Learning, మరియు Plant Disease కోసం ResNet50 వినియోగించలేదీ."
              : "All 8 models are runtime-verified against calibration datasets. Uses Random Forest for Crop Recommendation, LightGBM + Persistence Hybrid for Market Pricing, PPO Reinforcement Learning for Irrigation Scheduling, and ResNet50 Deep Learning for Plant Disease Diagnosis."}
          </div>
        </div>
      </div>
    );
  }
  /* ══════════════════════════════════════════════════════════
     SETTINGS VIEW
  ══════════════════════════════════════════════════════════ */
  function SettingsView() {
    return (
      <div className="card" style={{ maxWidth: 680 }}>
        <div className="card-header">
          <span className="card-title">
            <span className="card-title-icon"><SettingsIcon size={18} /></span>
            {t.navSettings}
          </span>
        </div>
        <div className="card-body">
          <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
            <div>
              <label className="field-label" style={{ fontWeight: 600 }}>
                {language === "te" ? "భాష ఎంపిక" : "Application Language"}
              </label>
              <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
                <button
                  type="button"
                  className={`btn-next ${language === "en" ? "" : "btn-back"}`}
                  onClick={() => setLanguage("en")}
                >
                  English
                </button>
                <button
                  type="button"
                  className={`btn-next ${language === "te" ? "" : "btn-back"}`}
                  onClick={() => setLanguage("te")}
                >
                  తెలుగు (Telugu)
                </button>
              </div>
            </div>

            <div>
              <label className="field-label" style={{ fontWeight: 600 }}>
                {language === "te" ? "API సర్వర్ చిరునామా" : "FastAPI Backend URL"}
              </label>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                className="form-input"
                style={{ marginTop: 6 }}
              />
              <span className="field-hint">
                {language === "te"
                  ? "స్థానిక సర్వర్: http://localhost:8000"
                  : "Default: http://localhost:8000. Verified with active CORS configuration."}
              </span>
            </div>

            <div style={{ padding: 14, background: "var(--page-bg)", borderRadius: "var(--r-md)" }}>
              <div style={{ fontWeight: 600, fontSize: "0.88rem", color: "var(--green-950)" }}>
                {language === "te" ? "డేటా నిల్వ స్థితి" : "Data Persistence Mode"}
              </div>
              <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)", marginTop: 4 }}>
                {storageMode === "sqlite_local"
                  ? (language === "te"
                      ? "SQLite లోకల్ డేటాబేస్ సక్రియం (.tmp/kshetraiq.db). అన్ని అసెస్‌మెంట్లు మరియు నివేదికలు సర్వర్ రీస్టార్ట్ అయినా సురక్షితంగా ఉంటాయి."
                      : "SQLite Local Database active (.tmp/kshetraiq.db). All farm assessments and generated advisory records are safely preserved across server restarts.")
                  : storageMode === "supabase"
                  ? (language === "te"
                      ? "సుపాబేస్ క్లౌడ్ డేటాబేస్ సక్రియం. బహుళ పరికరాల నుండి యాక్సెస్ చేయవచ్చు."
                      : "Supabase Cloud Database active. Multi-tenant records synchronized.")
                  : (language === "te"
                      ? "ప్రస్తుతం ఇన్-మెమరీ సెషన్ అమలులో ఉంది. సర్వర్ రీస్టార్ట్ అయితే రీసెట్ అవుతుంది. శాశ్వత నిల్వ కొరకు SQLite లేదా Supabase ను కాన్ఫిగర్ చేయండి."
                      : "In-memory development storage active. Server restarts reset local assessments. Configure Supabase in .env or SQLite for persistent records.")}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════════════════════════════════════════════════
     RENDER
  ══════════════════════════════════════════════════════════ */
  if (authChecking && !globalUser) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg-primary)", fontFamily: "Inter, sans-serif" }}>
        <div style={{ textAlign: "center" }}>
          <div style={{ width: 44, height: 44, border: "3px solid var(--green-200)", borderTopColor: "var(--green-700)", borderRadius: "50%", animation: "spin 1s linear infinite", margin: "0 auto 16px" }} />
          <p style={{ color: "var(--text-secondary)", fontSize: "0.95rem" }}>Verifying authenticated session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      {Sidebar()}
      <div className="main-area">
        {Topbar()}
        <main className="page-content">
          {view === "dashboard" && DashboardView()}
          {view === "profile" && ProfileView()}
          {view === "assessment" && AssessmentView()}
          {(view === "recommendations" || view === "results") && ResultsView()}
          {view === "weather" && WeatherView()}
          {view === "soil" && SoilHealthView()}
          {view === "irrigation" && IrrigationView()}
          {view === "market" && MarketView()}
          {view === "disease" && DiseaseView()}
          {view === "reports" && ReportsView()}
          {view === "registry" && RegistryView()}
          {view === "settings" && SettingsView()}
        </main>
      </div>

      {/* Auth Modal */}
      {showAuthModal && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
          <div className="modal-sheet" style={{ maxWidth: 420 }}>
            <div className="modal-header">
              <div className="modal-icon"><UserIcon size={22} /></div>
              <div>
                <div className="modal-title" id="auth-modal-title">
                  {language === "te" ? "రైతు ఖాతా" : "Farmer Account"}
                </div>
                <div className="modal-subtitle">
                  {language === "te" ? "సురక్షిత PBKDF2 ప్రమాణీకరణ" : "Secure PBKDF2 Authentication"}
                </div>
              </div>
              <button
                style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 4 }}
                onClick={() => setShowAuthModal(false)}
                aria-label="Close"
              >
                <XIcon size={18} />
              </button>
            </div>
            <div className="modal-body">
              <div className="auth-tab-bar">
                <button
                  className={`auth-tab-btn ${authTab === "login" ? "active" : ""}`}
                  onClick={() => { setAuthTab("login"); setAuthError(""); }}
                  type="button"
                >
                  {language === "te" ? "లాగిన్" : "Sign In"}
                </button>
                <button
                  className={`auth-tab-btn ${authTab === "register" ? "active" : ""}`}
                  onClick={() => { setAuthTab("register"); setAuthError(""); }}
                  type="button"
                >
                  {language === "te" ? "నమోదు" : "Register"}
                </button>
              </div>

              {authTab === "register" && (
                <div className="auth-form-group">
                  <label className="auth-form-label">{language === "te" ? "ప్రదర్శన పేరు" : "Display Name"}</label>
                  <input
                    type="text"
                    className="auth-form-input"
                    value={authDisplayName}
                    onChange={(e) => setAuthDisplayName(e.target.value)}
                    placeholder={language === "te" ? "రైతు పేరు" : "Farmer Name"}
                    id="auth-display-name"
                  />
                </div>
              )}

              <div className="auth-form-group">
                <label className="auth-form-label">{language === "te" ? "ఇ-మెయిల్" : "Email Address"}</label>
                <input
                  type="email"
                  className="auth-form-input"
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  placeholder="farmer@example.com"
                  id="auth-email"
                />
              </div>
              <div className="auth-form-group">
                <label className="auth-form-label">{language === "te" ? "పాస్‌వర్డ్" : "Password"}</label>
                <input
                  type="password"
                  className="auth-form-input"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  placeholder={authTab === "register" ? (language === "te" ? "కనీసం 6 అక్షరాలు" : "Min 6 characters") : "••••••••"}
                  id="auth-password"
                />
              </div>

              {authError && (
                <div style={{ padding: "8px 12px", background: "var(--red-bg)", borderRadius: "var(--r-sm)", fontSize: "0.8rem", color: "var(--red-text)", marginTop: 6 }}>
                  {authError}
                </div>
              )}

              <button
                className="auth-submit-btn"
                onClick={handleAuthSubmit}
                disabled={authLoading || !authEmail || !authPassword}
                type="button"
              >
                {authLoading
                  ? (language === "te" ? "ప్రమాణీకరిస్తోంది..." : "Authenticating...")
                  : authTab === "register"
                  ? (language === "te" ? "ఖాతా సృష్టించండి" : "Create Account")
                  : (language === "te" ? "సైన్ ఇన్" : "Sign In")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PDF Confirmation Modal */}
      {showReportModal && reportPreview && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title-id"
        >
          <div className="modal-sheet">
            <div className="modal-header">
              <div className="modal-icon">
                <FileTextIcon size={22} />
              </div>
              <div>
                <div className="modal-title" id="modal-title-id">{t.modalTitle}</div>
                <div className="modal-subtitle">
                  ReportLab PDF Engine · Formal Agronomic Summary
                </div>
              </div>
            </div>
            <div className="modal-body">
              <p className="modal-prompt">
                {language === "te"
                  ? reportPreview.confirmation_prompt_te
                  : reportPreview.confirmation_prompt}
              </p>
              <div className="modal-summary">
                {[
                  [language === "te" ? "పొలం:" : "Farm:", reportPreview.farm_name],
                  [language === "te" ? "స్థానం:" : "Location:", reportPreview.location],
                  [
                    language === "te" ? "విస్తీర్ణం & సీజన్:" : "Area & Season:",
                    `${reportPreview.acreage} Acres · ${reportPreview.season}`,
                  ],
                  [
                    language === "te" ? "సిఫార్సు పంట:" : "Recommended Crop:",
                    reportPreview.recommended_crop
                      ? `${reportPreview.recommended_crop} (${reportPreview.confidence ? `${Math.round(reportPreview.confidence * 100)}%` : "—"})`
                      : "—",
                  ],
                  [
                    language === "te" ? "నేల N-P-K-pH:" : "Soil N-P-K-pH:",
                    `N=${reportPreview.soil["N (kg/ha)"] ?? "—"}, P=${reportPreview.soil["P (kg/ha)"] ?? "—"}, K=${reportPreview.soil["K (kg/ha)"] ?? "—"}, pH=${reportPreview.soil["pH"] ?? "—"}`,
                  ],
                  [
                    language === "te" ? "వాతావరణం:" : "Agro-Meteo:",
                    `${reportPreview.weather["Temperature (°C)"] ?? "—"}°C, ${reportPreview.weather["Humidity (%)"] ?? "—"}%, ${reportPreview.weather["Rainfall (mm)"] ?? "—"}mm`,
                  ],
                ].map(([key, val]) => (
                  <div key={key} className="modal-summary-row">
                    <span className="modal-summary-key">{key}</span>
                    <span
                      className={`modal-summary-val ${key?.includes("Crop") || key?.includes("పంట") ? "crop-summary-highlight" : ""}`}
                    >
                      {val}
                    </span>
                  </div>
                ))}
              </div>
              <p className="modal-legal">{reportPreview.disclaimer}</p>

              {pdfError && (
                <div className="modal-error-box" role="alert">
                  <AlertCircleIcon size={14} />
                  <span>{pdfError}</span>
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setShowReportModal(false)}
                disabled={generatingPdf}
              >
                {t.cancelBtn}
              </button>
              <button
                type="button"
                className="btn-modal-confirm"
                onClick={confirmAndDownloadPdf}
                disabled={generatingPdf}
                id="btn-confirm-pdf"
              >
                {generatingPdf ? (
                  <>
                    <RefreshIcon size={15} className="spin" />
                    <span>{t.compilingPdf}</span>
                  </>
                ) : (
                  <>
                    <CheckCircleIcon size={15} />
                    <span>{t.confirmBtn}</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating Chatbot FAB */}
      <button
        type="button"
        className="chatbot-fab"
        onClick={() => {
          setChatOpen(!chatOpen);
          if (chatMinimized) setChatMinimized(false);
        }}
        aria-label="Toggle Agronomic Assistant"
        id="btn-chatbot-fab"
      >
        <BotIcon size={26} />
        <span className="fab-badge" />
      </button>

      {/* Chatbot Window */}
      {chatOpen && (
        <div className="chatbot-panel" style={chatMinimized ? { height: "auto" } : {}}>
          <div className="chatbot-header">
            <div className="chatbot-header-left">
              <div className="chatbot-header-icon">
                <BotIcon size={18} />
              </div>
              <div className="chatbot-header-text">
                <h3>{t.chatTitle}</h3>
                <span>
                  {llmConfigured ? `AI Provider: ${llmProviderName.toUpperCase()}` : t.chatSub}
                </span>
              </div>
            </div>
            <div className="chatbot-header-actions">
              <button
                type="button"
                onClick={handleClearChat}
                title={language === "te" ? "చాట్ క్లియర్ చేయండి" : "Clear Chat History"}
                aria-label="Clear Chat"
              >
                <TrashIcon size={14} />
              </button>
              <button
                type="button"
                onClick={() => setChatMinimized(!chatMinimized)}
                title={chatMinimized ? "Expand" : "Minimize"}
                aria-label="Minimize Chat"
              >
                <MinusIcon size={14} />
              </button>
              <button
                type="button"
                onClick={() => {
                  stopSpeaking();
                  setChatOpen(false);
                }}
                title="Close"
                aria-label="Close Chat"
              >
                <XIcon size={14} />
              </button>
            </div>
          </div>

          {!chatMinimized && (
            <>
              <div className="chatbot-messages">
                {chatMessages.map((msg, idx) => (
                  <div key={idx} className={`chat-msg ${msg.sender}`}>
                    {msg.sender === "bot" && (
                      <div style={{ display: "flex", gap: 6, marginBottom: 4, alignItems: "center", justifyContent: "space-between" }}>
                        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                          <span style={{ fontSize: "0.68rem", fontWeight: 600, color: "var(--green-700)" }}>
                            KshetraIQ
                          </span>
                          {msg.contextUsed && (
                            <span
                              style={{
                                fontSize: "0.62rem",
                                padding: "1px 6px",
                                borderRadius: 4,
                                background: "var(--green-100)",
                                color: "var(--green-800)",
                              }}
                            >
                              🌾 {language === "te" ? "పొలం వివరాలతో" : "Farm Context"}
                            </span>
                          )}
                          {msg.mode && (
                            <span
                              style={{
                                fontSize: "0.62rem",
                                padding: "1px 6px",
                                borderRadius: 4,
                                background: "#e8f0fe",
                                color: "#1a73e8",
                              }}
                            >
                              {msg.mode === "rule_based" ? "Rule Engine" : "LLM"}
                            </span>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            if (isSpeaking) {
                              stopSpeaking();
                            } else {
                              speakText(msg.text);
                            }
                          }}
                          title={isSpeaking ? "Stop Speaking" : "Read Aloud (TTS)"}
                          aria-label="Toggle text to speech"
                          style={{
                            background: "transparent",
                            border: "none",
                            cursor: "pointer",
                            color: isSpeaking ? "var(--green-700)" : "var(--text-muted)",
                            padding: 2,
                            display: "flex",
                            alignItems: "center",
                          }}
                        >
                          {isSpeaking ? <VolumeXIcon size={14} /> : <VolumeIcon size={14} />}
                        </button>
                      </div>
                    )}
                    <div>{msg.text}</div>
                    {msg.disclaimer && (
                      <div
                        style={{
                          marginTop: 6,
                          fontSize: "0.67rem",
                          color: "var(--text-muted)",
                          borderTop: "1px dashed rgba(0,0,0,0.1)",
                          paddingTop: 4,
                        }}
                      >
                        {msg.disclaimer}
                      </div>
                    )}
                  </div>
                ))}
                {chatLoading && (
                  <div className="chat-typing">
                    <span />
                    <span />
                    <span />
                  </div>
                )}
              </div>

              {/* Voice recognition status / error */}
              {isListening && (
                <div
                  style={{
                    padding: "6px 12px",
                    background: "var(--green-100)",
                    color: "var(--green-900)",
                    fontSize: "0.75rem",
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: "red",
                      display: "inline-block",
                      animation: "pulse 1s infinite",
                    }}
                  />
                  <span>
                    {language === "te"
                      ? "వింటున్నాను... మాట్లాడండి (తెలుగు)"
                      : "Listening... speak now (English)"}
                  </span>
                </div>
              )}
              {speechError && (
                <div
                  style={{
                    padding: "6px 12px",
                    background: "var(--amber-bg)",
                    color: "var(--amber-text)",
                    fontSize: "0.72rem",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span>{speechError}</span>
                  <button
                    type="button"
                    onClick={() => setSpeechError(null)}
                    style={{ background: "none", border: "none", cursor: "pointer", fontWeight: 700 }}
                  >
                    ×
                  </button>
                </div>
              )}

              {/* Quick suggestions */}
              <div
                style={{
                  display: "flex",
                  gap: 6,
                  padding: "8px 12px",
                  overflowX: "auto",
                  background: "var(--card-bg)",
                  borderTop: "1px solid var(--border)",
                }}
              >
                {[
                  language === "te" ? "నా నేల నివేదికను ఎలా అర్థం చేసుకోవాలి?" : "How do I interpret my soil report?",
                  language === "te" ? "నా నేల విలువలకు ఏ పంటలు సరిపోతాయి?" : "Which crops suit my soil measurements?",
                  language === "te" ? "నా తాజా పంట సిఫార్సును వివరించండి." : "Explain my latest crop recommendation.",
                  language === "te" ? "సాగునీటిని ఎలా ఆదా చేయవచ్చు?" : "How can I conserve irrigation water?",
                  language === "te" ? "సాయిల్ హెల్త్ రిపోర్ట్ ఎలా అప్‌లోడ్ చేయాలి?" : "How do I upload a soil health report?",
                  language === "te" ? "PDF నివేదికను ఎలా తయారు చేయాలి?" : "How do I generate a PDF report?",
                  language === "te" ? "ఒక మోడల్ ఎందుకు నిలిపివేయబడింది?" : "Why is a model marked unavailable?",
                ].map((promptText, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleSendMessage(promptText)}
                    disabled={chatLoading}
                    style={{
                      fontSize: "0.7rem",
                      padding: "4px 8px",
                      borderRadius: 12,
                      background: "var(--page-bg)",
                      border: "1px solid var(--border)",
                      color: "var(--green-800)",
                      whiteSpace: "nowrap",
                      cursor: "pointer",
                    }}
                  >
                    {promptText}
                  </button>
                ))}
              </div>

              <form
                className="chatbot-input-area"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
              >
                <button
                  type="button"
                  onClick={isListening ? () => setIsListening(false) : startVoiceInput}
                  disabled={chatLoading}
                  aria-label="Voice input"
                  id="btn-voice-chat"
                  style={{
                    background: isListening ? "var(--green-100)" : "transparent",
                    color: isListening ? "var(--green-700)" : "var(--text-muted)",
                    border: "none",
                    borderRadius: "50%",
                    width: 32,
                    height: 32,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    cursor: "pointer",
                    flexShrink: 0,
                  }}
                  title={
                    speechRecognitionSupported
                      ? language === "te"
                        ? "వాయిస్ ద్వారా మాట్లాడండి"
                        : "Speak using microphone"
                      : language === "te"
                      ? "బ్రౌజర్ వాయిస్‌కు మద్దతు ఇవ్వదు"
                      : "Voice unsupported in this browser"
                  }
                >
                  <MicIcon size={16} />
                </button>
                <input
                  type="text"
                  placeholder={t.chatPlaceholder}
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={chatLoading}
                  id="inp-chat-query"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || chatLoading}
                  aria-label="Send message"
                  id="btn-send-chat"
                >
                  <SendIcon size={16} />
                </button>
              </form>

              <div className="chatbot-disclaimer">{t.chatDisclaimer}</div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
