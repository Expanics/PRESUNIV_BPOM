import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ShieldCheckIcon, ZapIcon, HelpCircleIcon } from "lucide-react";
import { StepIndicator } from "./components/StepIndicator";
import { Step1Upload } from "./components/Step1Upload";
import { Step2Review } from "./components/Step2Review";
import { Step3Report } from "./components/Step3Report";

type Step = 1 | 2 | 3;

interface LoadingState {
  active: boolean;
  stage: number;
  message: string;
}

// Types for real backend data
export interface ComplianceRow {
  param: string;
  found: string;
  threshold: string;
  status: "PASS" | "FAIL" | "MISSING";
  dasarHukum: string;
  regulation: string;
  pasal: string;
}

export interface ViolationCard {
  id: string;
  namaParameter: string;
  nilaiTemuan: string;
  batasRegulasi: string;
  rekomendasi: string;
  severity: "high" | "medium" | "low";
}

export interface AnalysisSummary {
  pass: number;
  fail: number;
  missing: number;
  total: number;
  compliancePct: number;
}

export interface AnalysisResult {
  category: string;
  extracted: Record<string, unknown>;
  compliance: Record<string, unknown>;
  rows: ComplianceRow[];
  violationCards: ViolationCard[];
  narration: string;
  summary: AnalysisSummary;
}

const loadingStages = [
  { message: "Memproses dokumen...", duration: 800 },
  { message: "Mengidentifikasi kategori produk...", duration: 700 },
  { message: "Menjalankan rule engine BPOM...", duration: 900 },
  { message: "Menganalisis parameter uji...", duration: 1000 },
  { message: "Menyusun narasi AI...", duration: 600 },
];

const API_BASE = "/api";

export default function App() {
  const [step, setStep] = useState<Step>(1);
  const [loading, setLoading] = useState<LoadingState>({
    active: false,
    stage: 0,
    message: "",
  });
  const [direction, setDirection] = useState<1 | -1>(1);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [narration, setNarration] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (file: File | null, text: string) => {
    setError(null);
    setLoading({ active: true, stage: 0, message: loadingStages[0].message });

    // Animate loading stages
    let stageIdx = 0;
    const stageInterval = setInterval(() => {
      stageIdx = Math.min(stageIdx + 1, loadingStages.length - 1);
      setLoading((prev) => ({
        ...prev,
        stage: stageIdx,
        message: loadingStages[stageIdx].message,
      }));
    }, 800);

    try {
      const formData = new FormData();
      if (file) formData.append("file", file);
      if (text) formData.append("text", text);

      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        body: formData,
      });

      clearInterval(stageInterval);

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Terjadi kesalahan." }));
        throw new Error(err.detail || "Analisis gagal.");
      }

      const data: AnalysisResult = await res.json();
      
      // Efek transisi penyelesaian: fast-forward checklist yang tersisa
      const finishSequence = async () => {
        let current = stageIdx;
        while (current < loadingStages.length - 1) {
          current++;
          setLoading((prev) => ({
            ...prev,
            stage: current,
            message: loadingStages[current].message,
          }));
          await new Promise((r) => setTimeout(r, 500)); // Animasi centang cepat
        }
        
        // Memaksa state menjadi fully checked (stage === length)
        setLoading((prev) => ({
          ...prev,
          stage: loadingStages.length,
          message: "Selesai!",
        }));
        await new Promise((r) => setTimeout(r, 1000)); // Tahan sebentar di 100% biar terbaca
        
        setAnalysisResult(data);
        setNarration(data.narration);
        setLoading({ active: false, stage: 0, message: "" });
        setDirection(1);
        setStep(2);
      };

      await finishSequence();
    } catch (err: unknown) {
      clearInterval(stageInterval);
      setLoading({ active: false, stage: 0, message: "" });
      const message = err instanceof Error ? err.message : "Terjadi kesalahan tidak diketahui.";
      setError(message);
    }
  };

  const handleCategoryChange = async (newCategory: string) => {
    if (!analysisResult) return;
    setError(null);

    try {
      const formData = new FormData();
      formData.append("text", JSON.stringify(analysisResult.extracted));
      formData.append("category_override", newCategory);

      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) return;
      const data: AnalysisResult = await res.json();
      setAnalysisResult(data);
      setNarration(data.narration);
    } catch (err) {
      console.error("Category change failed:", err);
    }
  };

  const handleApprove = async () => {
    if (!analysisResult) return;
    setDirection(1);
    setStep(3);
  };

  const handleReset = () => {
    setDirection(-1);
    setAnalysisResult(null);
    setNarration("");
    setError(null);
    setTimeout(() => setStep(1), 10);
  };

  const variants = {
    enter: (dir: number) => ({
      opacity: 0,
      x: dir > 0 ? 24 : -24,
    }),
    center: {
      opacity: 1,
      x: 0,
    },
    exit: (dir: number) => ({
      opacity: 0,
      x: dir > 0 ? -24 : 24,
    }),
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC]">
      {/* Top Nav */}
      <header className="bg-[#1E3A5F] text-white px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center">
            <ShieldCheckIcon className="w-4 h-4 text-white" />
          </div>
          <div>
            <p style={{ fontWeight: 700, fontSize: "13px", letterSpacing: "-0.01em" }}>BPOM Compliance AI</p>
            <p className="text-blue-300 text-[10px]" style={{ fontWeight: 400 }}>Sistem Pengecekan Kepatuhan Pangan Otomatis</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-white/10 px-2.5 py-1 rounded-lg">
            <ZapIcon className="w-3 h-3 text-yellow-300" />
            <span className="text-[11px] text-blue-100" style={{ fontWeight: 500 }}>AI Engine v2.4</span>
          </div>
          <button className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors">
            <HelpCircleIcon className="w-4 h-4 text-blue-200" />
          </button>
        </div>
      </header>

      {/* Step Indicator */}
      <StepIndicator currentStep={step} />

      {/* Error Banner */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="mx-auto max-w-6xl px-6 mt-4"
          >
            <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3 flex items-center gap-2 text-sm text-red-700">
              <span style={{ fontWeight: 600 }}>⚠️ Error:</span> {error}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading Overlay */}
      <AnimatePresence>
        {loading.active && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white rounded-2xl p-8 shadow-2xl w-full max-w-sm mx-4"
            >
              <div className="flex flex-col items-center text-center">
                <div className="w-14 h-14 rounded-2xl bg-[#EFF6FF] flex items-center justify-center mb-5">
                  <ShieldCheckIcon className="w-7 h-7 text-[#2563EB]" />
                </div>
                <p style={{ fontWeight: 700, fontSize: "16px", color: "#0F172A" }} className="mb-1.5">Menganalisis Dokumen</p>
                <p className="text-sm text-slate-500 mb-6">{loading.message}</p>

                <div className="w-full space-y-2 mb-5">
                  {loadingStages.map((stage, i) => (
                    <div key={i} className="flex items-center gap-2.5">
                      <div
                        className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
                          i < loading.stage
                            ? "bg-[#16A34A]"
                            : i === loading.stage
                            ? "bg-[#2563EB]"
                            : "bg-slate-100"
                        }`}
                      >
                        {i < loading.stage ? (
                          <svg className="w-2 h-2 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : i === loading.stage ? (
                          <div className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                        ) : null}
                      </div>
                      <p
                        className={`text-xs transition-colors duration-300 ${
                          i < loading.stage
                            ? "text-[#16A34A]"
                            : i === loading.stage
                            ? "text-[#1E3A5F]"
                            : "text-slate-300"
                        }`}
                        style={{ fontWeight: i === loading.stage ? 600 : 400 }}
                      >
                        {stage.message}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-[#2563EB] rounded-full"
                    animate={{ width: `${((loading.stage + 1) / loadingStages.length) * 100}%` }}
                    transition={{ duration: 0.4 }}
                  />
                </div>
                <p className="text-[10px] text-slate-400 mt-2">
                  {loading.stage + 1} / {loadingStages.length}
                </p>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="pb-12 overflow-hidden">
        <AnimatePresence mode="wait" custom={direction}>
          {step === 1 && (
            <motion.div
              key="step1"
              custom={direction}
              variants={variants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.2, ease: "easeInOut" }}
            >
              <Step1Upload onAnalyze={handleAnalyze} isLoading={loading.active} />
            </motion.div>
          )}
          {step === 2 && analysisResult && (
            <motion.div
              key="step2"
              custom={direction}
              variants={variants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.2, ease: "easeInOut" }}
            >
              <Step2Review
                rows={analysisResult.rows}
                violationCards={analysisResult.violationCards}
                summary={analysisResult.summary}
                category={analysisResult.category}
                narration={narration}
                onNarrationChange={setNarration}
                onCategoryChange={handleCategoryChange}
                onApprove={handleApprove}
              />
            </motion.div>
          )}
          {step === 3 && analysisResult && (
            <motion.div
              key="step3"
              custom={direction}
              variants={variants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.2, ease: "easeInOut" }}
            >
              <Step3Report
                extracted={analysisResult.extracted}
                category={analysisResult.category}
                compliance={analysisResult.compliance}
                summary={analysisResult.summary}
                rows={analysisResult.rows}
                narration={narration}
                onReset={handleReset}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
