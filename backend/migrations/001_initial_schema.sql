-- KshetraIQ Database Schema for Supabase
-- Compliant with docs/ARCHITECTURE.md security boundaries and Row Level Security (RLS)

-- 1. Profiles Table
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    phone_number TEXT,
    preferred_language TEXT NOT NULL DEFAULT 'en' CHECK (preferred_language IN ('en', 'te')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view and manage their own profile"
    ON public.profiles
    FOR ALL
    USING (auth.uid() = id);

-- 2. Farms Table
CREATE TABLE IF NOT EXISTS public.farms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    farm_name TEXT NOT NULL,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    acreage NUMERIC(10, 2) NOT NULL CHECK (acreage > 0),
    irrigation_type TEXT NOT NULL,
    water_availability TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

ALTER TABLE public.farms ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Farmers can manage their own farms"
    ON public.farms
    FOR ALL
    USING (auth.uid() = farmer_id);

-- 3. Farm Assessments Table
CREATE TABLE IF NOT EXISTS public.farm_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    farm_id UUID REFERENCES public.farms(id) ON DELETE CASCADE,
    season TEXT NOT NULL,
    nitrogen_kg_ha NUMERIC(10, 2),
    phosphorus_kg_ha NUMERIC(10, 2),
    potassium_kg_ha NUMERIC(10, 2),
    ph NUMERIC(4, 2) CHECK (ph >= 0 AND ph <= 14),
    temperature_c NUMERIC(5, 2),
    humidity_percent NUMERIC(5, 2),
    rainfall_mm NUMERIC(10, 2),
    weather_source TEXT NOT NULL DEFAULT 'open_meteo_live',
    language TEXT NOT NULL DEFAULT 'en',
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

ALTER TABLE public.farm_assessments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Farmers can read and insert their own assessments"
    ON public.farm_assessments
    FOR ALL
    USING (auth.uid() = farmer_id OR farmer_id IS NULL);

-- 4. Prediction Runs Table
CREATE TABLE IF NOT EXISTS public.prediction_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES public.farm_assessments(id) ON DELETE CASCADE,
    model_id TEXT NOT NULL,
    status TEXT NOT NULL,
    prediction JSONB,
    missing_inputs TEXT[],
    contract_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

ALTER TABLE public.prediction_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Farmers can view prediction runs for their assessments"
    ON public.prediction_runs
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM public.farm_assessments a
        WHERE a.id = prediction_runs.assessment_id AND (a.farmer_id = auth.uid() OR a.farmer_id IS NULL)
    ));

-- 5. Report Jobs Table
CREATE TABLE IF NOT EXISTS public.report_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES public.farm_assessments(id) ON DELETE CASCADE,
    farmer_id UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    storage_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

ALTER TABLE public.report_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Farmers can access their own report jobs"
    ON public.report_jobs
    FOR ALL
    USING (auth.uid() = farmer_id OR farmer_id IS NULL);
