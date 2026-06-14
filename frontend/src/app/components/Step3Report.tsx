import { useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  DownloadIcon,
  FileTextIcon,
  CheckCircle2Icon,
  XCircleIcon,
  AlertTriangleIcon,
  PrinterIcon,
  ShieldCheckIcon,
  CalendarIcon,
} from "lucide-react";
import type { ComplianceRow, AnalysisSummary } from "../App";

interface Step3Props {
  extracted: Record<string, unknown>;
  category: string;
  compliance: Record<string, unknown>;
  summary: AnalysisSummary;
  rows: ComplianceRow[];
  narration: string;
  onReset: () => void;
}

const API_BASE = "/api";

export function Step3Report({
  extracted,
  category,
  compliance,
  summary,
  rows,
  narration,
  onReset,
}: Step3Props) {
  const [downloading, setDownloading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [reportReady, setReportReady] = useState(false);
  const [markdownPreview, setMarkdownPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const productName = (extracted?.nama_produk || extracted?.product_name || "Produk Tidak Diketahui") as string;
  const producer = (extracted?.produsen || extracted?.manufacturer || "-") as string;
  const batchNo = (extracted?.batch || extracted?.nomor_batch || "-") as string;
  const testDate = (extracted?.tanggal_uji || extracted?.test_date || "-") as string;
  const labName = (extracted?.laboratorium || extracted?.lab || "-") as string;
  const today = new Date().toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });

  const handleGenerateReport = async () => {
    setGenerating(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ extracted, category, compliance, narration }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Gagal generate report." }));
        throw new Error(err.detail);
      }

      const data = await res.json();
      setMarkdownPreview(data.markdown);
      setReportReady(data.pdfReady);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Terjadi kesalahan.");
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await fetch(`${API_BASE}/download`);
      if (!res.ok) throw new Error("PDF tidak tersedia.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "laporan_compliance_bpom.pdf";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed:", err);
    } finally {
      setTimeout(() => setDownloading(false), 1000);
    }
  };

  const handlePrint = () => window.print();

  const StatusBadge = ({ status }: { status: "PASS" | "FAIL" | "MISSING" }) => {
    if (status === "PASS") return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-[10px]" style={{ fontWeight: 700 }}>
        <CheckCircle2Icon className="w-2.5 h-2.5" />PASS
      </span>
    );
    if (status === "FAIL") return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-[10px]" style={{ fontWeight: 700 }}>
        <XCircleIcon className="w-2.5 h-2.5" />FAIL
      </span>
    );
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 text-[10px]" style={{ fontWeight: 700 }}>
        <AlertTriangleIcon className="w-2.5 h-2.5" />N/A
      </span>
    );
  };

  const isCompliant = summary.fail === 0;
  const compliancePct = summary.compliancePct;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 style={{ fontSize: "22px", fontWeight: 700, color: "#0F172A" }}>Laporan Final</h1>
          <p className="text-slate-500 mt-1 text-sm">Tinjau hasil analisis kepatuhan dan unduh laporan PDF.</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-slate-200 bg-white text-slate-600 text-xs hover:bg-slate-50 transition-colors"
            style={{ fontWeight: 500 }}
          >
            <PrinterIcon className="w-3.5 h-3.5" />
            Cetak
          </button>
          {!reportReady ? (
            <button
              onClick={handleGenerateReport}
              disabled={generating}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-[#2563EB] hover:bg-blue-700 text-white text-xs shadow-sm transition-all disabled:opacity-60"
              style={{ fontWeight: 600 }}
            >
              {generating ? (
                <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />Membuat laporan...</>
              ) : (
                <><FileTextIcon className="w-3.5 h-3.5" />Buat Laporan PDF</>
              )}
            </button>
          ) : (
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-[#1E3A5F] hover:bg-[#162d4a] text-white text-xs shadow-sm transition-all"
              style={{ fontWeight: 600 }}
            >
              {downloading ? (
                <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />Mengunduh...</>
              ) : (
                <><DownloadIcon className="w-3.5 h-3.5" />Download PDF</>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
          ⚠️ {error}
        </div>
      )}

      {/* Verdict Banner */}
      <div className={`rounded-xl border p-4 mb-5 flex items-center gap-3 ${
        isCompliant
          ? "border-green-200 bg-green-50"
          : "border-amber-200 bg-amber-50"
      }`}>
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
          isCompliant ? "bg-green-100" : "bg-amber-100"
        }`}>
          {isCompliant
            ? <CheckCircle2Icon className="w-5 h-5 text-[#16A34A]" />
            : <AlertTriangleIcon className="w-5 h-5 text-[#D97706]" />
          }
        </div>
        <div className="flex-1">
          <p style={{ fontWeight: 700, fontSize: "14px", color: isCompliant ? "#14532D" : "#92400E" }}>
            {isCompliant ? "Memenuhi Syarat — Siap Diajukan" : "Tidak Memenuhi Syarat — Perbaikan Diperlukan"}
          </p>
          <p className={`text-xs mt-0.5 ${isCompliant ? "text-green-700" : "text-amber-700"}`}>
            {isCompliant
              ? `Semua parameter memenuhi standar BPOM. Produk siap untuk proses registrasi.`
              : `Produk memiliki ${summary.fail} parameter yang tidak memenuhi batas regulasi BPOM. Perbaikan formulasi diperlukan sebelum pengajuan registrasi.`
            }
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <p style={{ fontWeight: 800, fontSize: "22px", color: isCompliant ? "#16A34A" : "#D97706", lineHeight: 1 }}>{compliancePct}%</p>
          <p className={`text-[10px] mt-0.5 ${isCompliant ? "text-green-600" : "text-amber-600"}`} style={{ fontWeight: 500 }}>Kepatuhan</p>
        </div>
      </div>

      {/* Report Preview Card */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden mb-5">
        {/* Report Header */}
        <div className="bg-[#1E3A5F] px-6 py-5 text-white">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <ShieldCheckIcon className="w-5 h-5 opacity-70" />
                <span className="text-[11px] opacity-60 uppercase tracking-wider" style={{ fontWeight: 600 }}>Laporan Kepatuhan BPOM</span>
              </div>
              <p style={{ fontWeight: 700, fontSize: "18px", lineHeight: 1.2 }}>{productName}</p>
              <p className="text-blue-200 text-xs mt-1">{producer}{batchNo !== "-" ? ` — Batch ${batchNo}` : ""}</p>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-1.5 text-blue-200 text-xs mb-1 justify-end">
                <CalendarIcon className="w-3 h-3" />
                <span>{today}</span>
              </div>
              <p className="text-[10px] text-blue-300" style={{ fontFamily: "monospace" }}>Kategori: {category}</p>
            </div>
          </div>
        </div>

        {/* Report Body */}
        <div className="p-6">
          {/* Product Info */}
          <div className="mb-6">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-3" style={{ fontWeight: 600 }}>Informasi Produk</p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: "Nama Produk", value: productName },
                { label: "Produsen", value: producer },
                { label: "Nomor Batch", value: batchNo },
                { label: "Kategori BPOM", value: category },
                { label: "Tanggal Uji", value: testDate },
                { label: "Laboratorium", value: labName },
                { label: "Tanggal Laporan", value: today },
              ].map((item, i) => (
                <div key={i} className="bg-slate-50 rounded-lg p-3">
                  <p className="text-[10px] text-slate-400 mb-1" style={{ fontWeight: 500 }}>{item.label}</p>
                  <p className="text-xs text-slate-800" style={{ fontWeight: 600 }}>{item.value || "-"}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Executive Summary */}
          <div className="mb-6">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-3" style={{ fontWeight: 600 }}>Ringkasan Eksekutif</p>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
              {[
                { label: "Total Parameter", value: String(summary.total), icon: null, color: "text-slate-700" },
                { label: "Parameter PASS", value: String(summary.pass), icon: <CheckCircle2Icon className="w-4 h-4 text-[#16A34A]" />, color: "text-[#16A34A]" },
                { label: "Parameter FAIL", value: String(summary.fail), icon: <XCircleIcon className="w-4 h-4 text-[#DC2626]" />, color: "text-[#DC2626]" },
                { label: "Data Tidak Ada", value: String(summary.missing), icon: <AlertTriangleIcon className="w-4 h-4 text-[#D97706]" />, color: "text-[#D97706]" },
                { label: "Tingkat Kepatuhan", value: `${compliancePct}%`, icon: null, color: "text-[#1E3A5F]" },
                { label: "Rekomendasi", value: isCompliant ? "Siap Diajukan" : "Perbaikan Formulasi", icon: null, color: isCompliant ? "text-[#16A34A]" : "text-[#D97706]" },
              ].map((s, i) => (
                <div key={i} className="flex items-center gap-2.5 bg-slate-50 rounded-lg p-3">
                  {s.icon && <div className="flex-shrink-0">{s.icon}</div>}
                  <div>
                    <p className="text-[10px] text-slate-400" style={{ fontWeight: 500 }}>{s.label}</p>
                    <p className={`text-sm ${s.color}`} style={{ fontWeight: 700 }}>{s.value}</p>
                  </div>
                </div>
              ))}
            </div>
            {narration && (
              <div className="bg-slate-50 rounded-lg p-4 border-l-4 border-[#1E3A5F]">
                <div className="text-xs text-slate-700 leading-relaxed">
                  <ReactMarkdown
                    components={{
                      h1: ({node, ...props}: any) => <h1 className="text-sm font-bold mt-2 mb-2 text-slate-900" {...props}/>,
                      h2: ({node, ...props}: any) => <h2 className="text-[13px] font-bold mt-2 mb-2 text-slate-900" {...props}/>,
                      h3: ({node, ...props}: any) => <h3 className="text-xs font-bold mt-2 mb-1 text-slate-900" {...props}/>,
                      p: ({node, ...props}: any) => <p className="mb-2 last:mb-0" {...props}/>,
                      strong: ({node, ...props}: any) => <strong className="font-bold text-slate-900" {...props}/>,
                      ul: ({node, ...props}: any) => <ul className="list-disc pl-4 mb-2 space-y-1" {...props}/>,
                      ol: ({node, ...props}: any) => <ol className="list-decimal pl-4 mb-2 space-y-1" {...props}/>,
                      li: ({node, ...props}: any) => <li className="" {...props}/>,
                    }}
                  >
                    {narration}
                  </ReactMarkdown>
                </div>
              </div>
            )}
          </div>

          {/* Detail Results Table */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <FileTextIcon className="w-3.5 h-3.5 text-slate-400" />
              <p className="text-xs text-slate-500 uppercase tracking-wider" style={{ fontWeight: 600 }}>Detail Hasil Uji</p>
            </div>
            <div className="rounded-lg border border-slate-200 overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200">
                    <th className="text-left px-4 py-2 text-slate-500" style={{ fontWeight: 600, fontSize: "10px", textTransform: "uppercase" }}>Parameter</th>
                    <th className="text-right px-4 py-2 text-slate-500" style={{ fontWeight: 600, fontSize: "10px", textTransform: "uppercase" }}>Nilai Uji</th>
                    <th className="text-left px-4 py-2 text-slate-500" style={{ fontWeight: 600, fontSize: "10px", textTransform: "uppercase" }}>Batas BPOM</th>
                    <th className="text-center px-4 py-2 text-slate-500" style={{ fontWeight: 600, fontSize: "10px", textTransform: "uppercase" }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, i) => (
                    <tr
                      key={i}
                      className={`border-b border-slate-100 last:border-0 ${row.status === "FAIL" ? "bg-red-50/50" : row.status === "MISSING" ? "bg-amber-50/30" : ""}`}
                      style={{ borderLeft: `3px solid ${row.status === "PASS" ? "#16A34A" : row.status === "FAIL" ? "#DC2626" : "#D97706"}` }}
                    >
                      <td className="px-4 py-2 text-slate-700" style={{ fontWeight: 500 }}>{row.param}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-slate-600" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{row.found}</td>
                      <td className="px-4 py-2 text-slate-500" style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px" }}>{row.threshold}</td>
                      <td className="px-4 py-2 text-center"><StatusBadge status={row.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Report Footer */}
        <div className="bg-slate-50 border-t border-slate-100 px-6 py-3 flex items-center justify-between text-[10px] text-slate-400">
          <span>Dibuat oleh BPOM Compliance AI System — bukan pengganti konsultasi regulasi resmi.</span>
          <span style={{ fontFamily: "monospace" }}>v2.4.1 · {today}</span>
        </div>
      </div>

      {/* Markdown Preview (if generated) */}
      {markdownPreview && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-5">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-3" style={{ fontWeight: 600 }}>Preview Laporan (Markdown)</p>
          <pre className="text-xs text-slate-700 whitespace-pre-wrap leading-relaxed overflow-auto max-h-64 bg-slate-50 rounded-lg p-4 border border-slate-100">
            {markdownPreview}
          </pre>
        </div>
      )}

      {/* New Analysis Button */}
      <div className="flex justify-center">
        <button
          onClick={onReset}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg border border-slate-200 bg-white text-slate-600 text-sm hover:bg-slate-50 hover:border-slate-300 transition-all"
          style={{ fontWeight: 500 }}
        >
          + Mulai Analisis Baru
        </button>
      </div>
    </div>
  );
}
