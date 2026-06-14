import { useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  CheckCircle2Icon,
  XCircleIcon,
  AlertTriangleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  InfoIcon,
  EditIcon,
  CheckIcon,
} from "lucide-react";
import type { ComplianceRow, ViolationCard, AnalysisSummary } from "../App";

const CATEGORIES = ["SUPLEMEN", "DAIRY", "DAGING_OLAHAN", "BUAH_SAYUR"];

interface Step2Props {
  rows: ComplianceRow[];
  violationCards: ViolationCard[];
  summary: AnalysisSummary;
  category: string;
  narration: string;
  onNarrationChange: (val: string) => void;
  onCategoryChange: (cat: string) => void;
  onApprove: () => void;
}

export function Step2Review({
  rows,
  violationCards,
  summary,
  category,
  narration,
  onNarrationChange,
  onCategoryChange,
  onApprove,
}: Step2Props) {
  const [selectedCategory, setSelectedCategory] = useState(category);
  const [editingCategory, setEditingCategory] = useState(false);
  const [expandedViolations, setExpandedViolations] = useState<Set<string>>(
    new Set(violationCards.length > 0 ? [violationCards[0].id] : [])
  );
  const [reviewed, setReviewed] = useState(false);

  const [previewMode, setPreviewMode] = useState(true);

  const toggleViolation = (id: string) => {
    setExpandedViolations((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCategoryConfirm = () => {
    setEditingCategory(false);
    onCategoryChange(selectedCategory);
  };

  const severityColors = {
    high: "bg-red-50 border-red-200 text-red-700",
    medium: "bg-amber-50 border-amber-200 text-amber-700",
    low: "bg-blue-50 border-blue-200 text-blue-600",
  };

  const severityLabels = {
    high: "Kritikal",
    medium: "Sedang",
    low: "Perlu Data",
  };

  const markdownComponents = {
    h1: ({node, ...props}: any) => <h1 className="text-lg font-bold mt-2 mb-2 text-slate-900" {...props}/>,
    h2: ({node, ...props}: any) => <h2 className="text-base font-bold mt-2 mb-2 text-slate-900" {...props}/>,
    h3: ({node, ...props}: any) => <h3 className="text-sm font-bold mt-2 mb-1 text-slate-900" {...props}/>,
    p: ({node, ...props}: any) => <p className="mb-2 last:mb-0 leading-relaxed" {...props}/>,
    strong: ({node, ...props}: any) => <strong className="font-bold text-slate-900" {...props}/>,
    ul: ({node, ...props}: any) => <ul className="list-disc pl-5 mb-2 space-y-1" {...props}/>,
    ol: ({node, ...props}: any) => <ol className="list-decimal pl-5 mb-2 space-y-1" {...props}/>,
    li: ({node, ...props}: any) => <li className="" {...props}/>,
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 style={{ fontSize: "22px", fontWeight: 700, color: "#0F172A" }}>Review Hasil AI</h1>
          <p className="text-slate-500 mt-1 text-sm">Periksa hasil analisis kepatuhan dan narasi AI sebelum membuat laporan final.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400" style={{ fontWeight: 500 }}>Kategori Produk:</span>
          {editingCategory ? (
            <div className="flex items-center gap-1.5">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="text-xs border border-[#2563EB] rounded-lg px-2.5 py-1.5 text-[#1E3A5F] bg-blue-50 outline-none"
                style={{ fontWeight: 600 }}
              >
                {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
              </select>
              <button
                onClick={handleCategoryConfirm}
                className="w-6 h-6 rounded-full bg-[#16A34A] flex items-center justify-center"
              >
                <CheckIcon className="w-3 h-3 text-white" />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setEditingCategory(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#EFF6FF] border border-blue-100 text-[#1E3A5F] text-xs hover:bg-blue-100 transition-colors group"
              style={{ fontWeight: 600 }}
            >
              {selectedCategory}
              <EditIcon className="w-3 h-3 text-[#2563EB] opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center flex-shrink-0">
            <CheckCircle2Icon className="w-5 h-5 text-[#16A34A]" />
          </div>
          <div>
            <p className="text-2xl text-[#16A34A]" style={{ fontWeight: 700, lineHeight: 1.1 }}>{summary.pass}</p>
            <p className="text-xs text-slate-500 mt-0.5" style={{ fontWeight: 500 }}>Parameter PASS</p>
          </div>
          <div className="ml-auto">
            <div className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full border border-green-100" style={{ fontWeight: 600 }}>
              {summary.total > 0 ? Math.round((summary.pass / summary.total) * 100) : 0}%
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center flex-shrink-0">
            <XCircleIcon className="w-5 h-5 text-[#DC2626]" />
          </div>
          <div>
            <p className="text-2xl text-[#DC2626]" style={{ fontWeight: 700, lineHeight: 1.1 }}>{summary.fail}</p>
            <p className="text-xs text-slate-500 mt-0.5" style={{ fontWeight: 500 }}>Parameter FAIL</p>
          </div>
          <div className="ml-auto">
            <div className="text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-100" style={{ fontWeight: 600 }}>
              {summary.total > 0 ? Math.round((summary.fail / summary.total) * 100) : 0}%
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center flex-shrink-0">
            <AlertTriangleIcon className="w-5 h-5 text-[#D97706]" />
          </div>
          <div>
            <p className="text-2xl text-[#D97706]" style={{ fontWeight: 700, lineHeight: 1.1 }}>{summary.missing}</p>
            <p className="text-xs text-slate-500 mt-0.5" style={{ fontWeight: 500 }}>Data Tidak Lengkap</p>
          </div>
          <div className="ml-auto">
            <div className="text-xs text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100" style={{ fontWeight: 600 }}>
              {summary.total > 0 ? Math.round((summary.missing / summary.total) * 100) : 0}%
            </div>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-5">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-slate-500" style={{ fontWeight: 500 }}>Tingkat Kepatuhan Keseluruhan</p>
          <p className="text-xs text-slate-700" style={{ fontWeight: 600 }}>{summary.pass} / {summary.total} parameter</p>
        </div>
        <div className="h-2 bg-slate-100 rounded-full overflow-hidden flex">
          <div className="bg-[#16A34A] h-full transition-all" style={{ width: `${summary.total > 0 ? (summary.pass / summary.total) * 100 : 0}%` }} />
          <div className="bg-[#DC2626] h-full transition-all" style={{ width: `${summary.total > 0 ? (summary.fail / summary.total) * 100 : 0}%` }} />
          <div className="bg-[#D97706] h-full transition-all" style={{ width: `${summary.total > 0 ? (summary.missing / summary.total) * 100 : 0}%` }} />
        </div>
        <div className="flex items-center gap-4 mt-2">
          <span className="flex items-center gap-1 text-[10px] text-slate-500"><span className="w-2 h-2 rounded-full bg-[#16A34A] inline-block" />PASS</span>
          <span className="flex items-center gap-1 text-[10px] text-slate-500"><span className="w-2 h-2 rounded-full bg-[#DC2626] inline-block" />FAIL</span>
          <span className="flex items-center gap-1 text-[10px] text-slate-500"><span className="w-2 h-2 rounded-full bg-[#D97706] inline-block" />MISSING</span>
        </div>
      </div>

      {/* Compliance Table */}
      <div className="bg-white rounded-xl border border-slate-200 mb-5 overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-2">
          <p style={{ fontWeight: 600, fontSize: "13px", color: "#0F172A" }}>Tabel Hasil Uji Kepatuhan</p>
          <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full" style={{ fontWeight: 500 }}>
            {rows.length} parameter
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-left px-4 py-2.5 text-slate-500 w-[200px]" style={{ fontWeight: 600, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em" }}>Parameter</th>
                <th className="text-right px-4 py-2.5 text-slate-500" style={{ fontWeight: 600, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em" }}>Nilai Uji</th>
                <th className="text-left px-4 py-2.5 text-slate-500" style={{ fontWeight: 600, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em" }}>Batas BPOM</th>
                <th className="text-center px-4 py-2.5 text-slate-500 w-[80px]" style={{ fontWeight: 600, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em" }}>Status</th>
                <th className="text-left px-4 py-2.5 text-slate-500" style={{ fontWeight: 600, fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em" }}>Dasar Hukum</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr
                  key={i}
                  className={`border-b border-slate-50 transition-colors ${
                    row.status === "FAIL"
                      ? "bg-red-50/60 hover:bg-red-50"
                      : row.status === "MISSING"
                      ? "bg-amber-50/40 hover:bg-amber-50"
                      : i % 2 === 0
                      ? "bg-white hover:bg-slate-50/80"
                      : "bg-slate-50/30 hover:bg-slate-50/80"
                  }`}
                  style={{
                    borderLeft: row.status === "FAIL" ? "3px solid #DC2626" : row.status === "PASS" ? "3px solid #16A34A" : "3px solid #D97706",
                  }}
                >
                  <td className="px-4 py-2.5 text-slate-800" style={{ fontWeight: 500 }}>{row.param}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums" style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: row.status === "FAIL" ? 600 : 400, color: row.status === "FAIL" ? "#DC2626" : "#374151" }}>
                    {row.found !== "-" ? row.found : "—"}
                  </td>
                  <td className="px-4 py-2.5 text-slate-600" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px" }}>{row.threshold}</td>
                  <td className="px-4 py-2.5 text-center">
                    {row.status === "PASS" && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700" style={{ fontWeight: 700, fontSize: "10px" }}>
                        <CheckCircle2Icon className="w-2.5 h-2.5" />PASS
                      </span>
                    )}
                    {row.status === "FAIL" && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-100 text-red-700" style={{ fontWeight: 700, fontSize: "10px" }}>
                        <XCircleIcon className="w-2.5 h-2.5" />FAIL
                      </span>
                    )}
                    {row.status === "MISSING" && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700" style={{ fontWeight: 700, fontSize: "10px" }}>
                        <AlertTriangleIcon className="w-2.5 h-2.5" />N/A
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5">
                    <div className="relative group">
                      <span className="text-[#2563EB] cursor-help underline decoration-dotted underline-offset-2 truncate block max-w-[180px]" style={{ fontWeight: 500, fontSize: "11px" }}>
                        {row.dasarHukum}
                      </span>
                      {row.dasarHukum && row.dasarHukum !== "-" && (
                        <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block z-50 w-72 p-3 bg-[#1E3A5F] text-white rounded-lg shadow-xl text-[11px] leading-relaxed pointer-events-none">
                          <div className="flex items-start gap-1.5">
                            <InfoIcon className="w-3 h-3 flex-shrink-0 mt-0.5 opacity-70" />
                            <span>{row.dasarHukum}</span>
                          </div>
                          <div className="absolute top-full left-3 w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-[#1E3A5F]" />
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* AI Narration & Violation Cards */}
      {violationCards.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 mb-5 overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <p style={{ fontWeight: 600, fontSize: "13px", color: "#0F172A" }}>Penjelasan AI — Temuan Pelanggaran</p>
              <span className="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full" style={{ fontWeight: 500 }}>
                {violationCards.length} temuan
              </span>
            </div>
            <button
              onClick={() => setExpandedViolations(
                expandedViolations.size === violationCards.length
                  ? new Set()
                  : new Set(violationCards.map((v) => v.id))
              )}
              className="text-[11px] text-[#2563EB] hover:underline"
              style={{ fontWeight: 500 }}
            >
              {expandedViolations.size === violationCards.length ? "Tutup semua" : "Buka semua"}
            </button>
          </div>

          <div className="divide-y divide-slate-100">
            {violationCards.map((v) => (
              <div key={v.id} className="px-5">
                <button
                  onClick={() => toggleViolation(v.id)}
                  className="w-full flex items-center gap-3 py-3.5 text-left hover:bg-slate-50 -mx-5 px-5 transition-colors"
                >
                  <span className={`px-2 py-0.5 rounded text-[10px] border flex-shrink-0 ${severityColors[v.severity]}`} style={{ fontWeight: 700 }}>
                    {severityLabels[v.severity]}
                  </span>
                  <span className="text-sm text-slate-800 flex-1" style={{ fontWeight: 600 }}>{v.namaParameter}</span>
                  <span className="text-[11px] text-slate-400 tabular-nums mr-3" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                    {v.nilaiTemuan}
                  </span>
                  {expandedViolations.has(v.id)
                    ? <ChevronUpIcon className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    : <ChevronDownIcon className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  }
                </button>

                {expandedViolations.has(v.id) && (
                  <div className="pb-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="rounded-lg bg-slate-50 border border-slate-100 p-3.5">
                      <p className="text-[10px] text-slate-400 uppercase tracking-wider mb-2" style={{ fontWeight: 600 }}>Perbandingan Nilai</p>
                      <div className="flex items-start gap-3">
                        <div>
                          <p className="text-[10px] text-slate-500" style={{ fontWeight: 500 }}>Nilai Temuan</p>
                          <p className="text-sm text-[#DC2626] tabular-nums" style={{ fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>{v.nilaiTemuan}</p>
                        </div>
                        <div className="text-slate-300 self-center">→</div>
                        <div>
                          <p className="text-[10px] text-slate-500" style={{ fontWeight: 500 }}>Batas Regulasi</p>
                          <p className="text-sm text-[#16A34A] tabular-nums" style={{ fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>
                            {v.batasRegulasi.split("(")[0].trim()}
                          </p>
                        </div>
                      </div>
                      <p className="text-[10px] text-slate-400 mt-2">{v.batasRegulasi.match(/\(.*\)/)?.[0] || ""}</p>
                    </div>

                    <div className="rounded-lg bg-blue-50/50 border border-blue-100 p-3.5">
                      <p className="text-[10px] text-[#1E3A5F] uppercase tracking-wider mb-2" style={{ fontWeight: 600 }}>Rekomendasi</p>
                      <p className="text-xs text-slate-600 leading-relaxed italic">{v.rekomendasi}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Editable Narration */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-5">
        <div className="flex items-center justify-between mb-3">
          <p className="text-xs text-slate-500 uppercase tracking-wider" style={{ fontWeight: 600 }}>Narasi AI — Dapat Diedit</p>
          <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded-lg">
            <button 
              onClick={() => setPreviewMode(true)}
              className={`px-3 py-1.5 text-[11px] rounded-md transition-colors ${previewMode ? "bg-white text-slate-800 shadow-sm font-semibold" : "text-slate-500 font-medium hover:text-slate-700"}`}
            >
              Preview
            </button>
            <button 
              onClick={() => setPreviewMode(false)}
              className={`px-3 py-1.5 text-[11px] rounded-md transition-colors ${!previewMode ? "bg-white text-slate-800 shadow-sm font-semibold" : "text-slate-500 font-medium hover:text-slate-700"}`}
            >
              Edit Teks
            </button>
          </div>
        </div>

        {previewMode ? (
          <div className="w-full text-sm text-slate-700 border border-slate-200 rounded-lg p-4 bg-slate-50/50 min-h-[144px]">
            <ReactMarkdown components={markdownComponents}>
              {narration || "*Narasi kosong*"}
            </ReactMarkdown>
          </div>
        ) : (
          <textarea
            value={narration}
            onChange={(e) => onNarrationChange(e.target.value)}
            rows={6}
            className="w-full text-sm text-slate-700 border border-[#2563EB] rounded-lg p-3 resize-none outline-none ring-2 ring-blue-100 transition-all leading-relaxed bg-white"
            style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px" }}
          />
        )}
      </div>

      {/* Review CTA */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4 flex-wrap">
        <div className="flex items-start gap-3 flex-1">
          <input
            type="checkbox"
            id="reviewed"
            checked={reviewed}
            onChange={(e) => setReviewed(e.target.checked)}
            className="mt-0.5 w-4 h-4 accent-[#1E3A5F] cursor-pointer"
          />
          <label htmlFor="reviewed" className="text-sm text-slate-700 cursor-pointer leading-relaxed" style={{ fontWeight: 500 }}>
            Saya telah memeriksa seluruh hasil analisis dan menyetujui narasi AI untuk dimasukkan ke dalam laporan final.
          </label>
        </div>
        <button
          onClick={onApprove}
          disabled={!reviewed}
          className={`flex items-center gap-2 px-6 py-3 rounded-xl text-sm transition-all duration-200 flex-shrink-0 ${
            reviewed
              ? "bg-[#1E3A5F] hover:bg-[#162d4a] text-white shadow-md cursor-pointer"
              : "bg-slate-100 text-slate-400 cursor-not-allowed"
          }`}
          style={{ fontWeight: 600 }}
        >
          Setuju & Buat Laporan Final
          <span className="opacity-70">→</span>
        </button>
      </div>
    </div>
  );
}
