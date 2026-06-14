import { useState, useRef, useCallback } from "react";
import { UploadCloudIcon, FileTextIcon, XIcon, AlertCircleIcon, Loader2Icon } from "lucide-react";

interface Step1Props {
  onAnalyze: (file: File | null, text: string) => void;
  isLoading: boolean;
}

export function Step1Upload({ onAnalyze, isLoading }: Step1Props) {
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [manualText, setManualText] = useState("");
  const [activeInput, setActiveInput] = useState<"file" | "text" | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.type === "application/pdf" || file.name.endsWith(".docx"))) {
      setUploadedFile(file);
      setActiveInput("file");
      setManualText("");
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      setActiveInput("file");
      setManualText("");
    }
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setManualText(e.target.value);
    setActiveInput(e.target.value.length > 0 ? "text" : null);
    if (e.target.value.length > 0) setUploadedFile(null);
  };

  const canAnalyze =
    (activeInput === "file" && uploadedFile !== null) ||
    (activeInput === "text" && manualText.trim().length > 50);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleSubmit = () => {
    if (!canAnalyze || isLoading) return;
    onAnalyze(uploadedFile, manualText);
  };

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 style={{ fontSize: "22px", fontWeight: 700, color: "#0F172A" }}>Input Dokumen</h1>
        <p className="text-slate-500 mt-1 text-sm">
          Upload laporan uji laboratorium produk pangan atau tempel teks secara manual untuk dianalisis.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Upload Panel */}
        <div
          className={`bg-white rounded-xl border-2 transition-all duration-200 flex flex-col ${
            dragOver
              ? "border-[#2563EB] bg-blue-50 shadow-lg shadow-blue-100"
              : uploadedFile
              ? "border-[#16A34A] bg-green-50"
              : activeInput === "text"
              ? "border-slate-200 opacity-50 pointer-events-none"
              : "border-dashed border-slate-200 hover:border-slate-300"
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <div className="p-6 flex-1">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-[#EFF6FF] flex items-center justify-center">
                <UploadCloudIcon className="w-4 h-4 text-[#2563EB]" />
              </div>
              <div>
                <p style={{ fontWeight: 600, fontSize: "14px", color: "#0F172A" }}>Upload Dokumen</p>
                <p className="text-[11px] text-slate-400">Drag & drop atau klik untuk browse</p>
              </div>
              <div className="ml-auto flex gap-1.5">
                <span className="px-2 py-0.5 rounded text-[10px] bg-red-50 text-red-600 border border-red-100" style={{ fontWeight: 600 }}>PDF</span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-blue-50 text-blue-600 border border-blue-100" style={{ fontWeight: 600 }}>DOCX</span>
              </div>
            </div>

            {uploadedFile ? (
              <div className="rounded-lg bg-white border border-[#16A34A]/30 p-3 flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-green-50 flex items-center justify-center flex-shrink-0">
                  <FileTextIcon className="w-4 h-4 text-[#16A34A]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-800 truncate" style={{ fontWeight: 500 }}>{uploadedFile.name}</p>
                  <p className="text-[11px] text-slate-400">{formatFileSize(uploadedFile.size)}</p>
                </div>
                <button
                  onClick={() => { setUploadedFile(null); setActiveInput(null); }}
                  className="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
                >
                  <XIcon className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div
                className="border-2 border-dashed border-slate-200 rounded-lg p-8 text-center cursor-pointer hover:border-[#2563EB] hover:bg-blue-50/50 transition-all duration-150"
                onClick={() => fileInputRef.current?.click()}
              >
                <UploadCloudIcon className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500" style={{ fontWeight: 500 }}>Klik atau drag file ke sini</p>
                <p className="text-[11px] text-slate-400 mt-1">Maksimal 25 MB per file</p>
              </div>
            )}

            <input ref={fileInputRef} type="file" accept=".pdf,.docx" className="hidden" onChange={handleFileChange} />
          </div>

          {!uploadedFile && !dragOver && (
            <div className="px-6 pb-5">
              <div className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg border border-amber-100">
                <AlertCircleIcon className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                <p className="text-[11px] text-amber-700">
                  Pastikan dokumen berisi data uji laboratorium lengkap termasuk parameter, nilai, dan satuan ukuran.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Manual Text Panel */}
        <div
          className={`bg-white rounded-xl border transition-all duration-200 flex flex-col ${
            activeInput === "file"
              ? "border-slate-200 opacity-50 pointer-events-none"
              : activeInput === "text"
              ? "border-[#2563EB] shadow-sm shadow-blue-100"
              : "border-slate-200 hover:border-slate-300"
          }`}
        >
          <div className="p-6 flex-1 flex flex-col">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center">
                <FileTextIcon className="w-4 h-4 text-slate-500" />
              </div>
              <div>
                <p style={{ fontWeight: 600, fontSize: "14px", color: "#0F172A" }}>Input Teks Manual</p>
                <p className="text-[11px] text-slate-400">Salin dan tempel data lab report</p>
              </div>
              {manualText.length > 0 && (
                <span className="ml-auto text-[11px] text-slate-400 tabular-nums">
                  {manualText.length.toLocaleString()} karakter
                </span>
              )}
            </div>

            <textarea
              value={manualText}
              onChange={handleTextChange}
              placeholder={`Tempel teks laporan uji lab di sini...\n\nContoh:\nNama Produk: Biskuit Gandum Premium\nProdusen: PT. Agro Pangan Nusantara\n\nParameter Uji:\n- Kadar Air: 4,2% (SNI maks. 5%)\n- Protein: 8,1 g/100g\n- Lemak Total: 18,3 g/100g\n...`}
              className="flex-1 resize-none text-sm text-slate-700 placeholder:text-slate-300 outline-none w-full min-h-[220px] leading-relaxed"
              style={{ fontFamily: "'Inter', sans-serif", fontWeight: 400 }}
            />

            {manualText.length > 0 && manualText.length < 50 && (
              <p className="text-[11px] text-amber-600 mt-2">
                Minimal 50 karakter diperlukan untuk analisis yang akurat.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="flex items-center gap-3 my-5">
        <div className="flex-1 h-px bg-slate-200" />
        <span className="text-[11px] text-slate-400 uppercase tracking-wider" style={{ fontWeight: 600 }}>atau pilih salah satu</span>
        <div className="flex-1 h-px bg-slate-200" />
      </div>

      {/* CTA */}
      <button
        onClick={handleSubmit}
        disabled={!canAnalyze || isLoading}
        id="analyze-btn"
        className={`w-full flex items-center justify-center gap-2.5 py-3.5 rounded-xl text-sm transition-all duration-200 ${
          canAnalyze && !isLoading
            ? "bg-[#1E3A5F] hover:bg-[#162d4a] text-white shadow-md hover:shadow-lg cursor-pointer"
            : "bg-slate-100 text-slate-400 cursor-not-allowed"
        }`}
        style={{ fontWeight: 600, fontSize: "14px" }}
      >
        {isLoading ? (
          <>
            <Loader2Icon className="w-4 h-4 animate-spin" />
            Menganalisis dokumen...
          </>
        ) : (
          <>
            Analisis Dokumen
            <span className="text-xs opacity-70">→</span>
          </>
        )}
      </button>

      {!canAnalyze && !isLoading && (
        <p className="text-center text-[11px] text-slate-400 mt-2">
          Upload dokumen atau tempel teks terlebih dahulu untuk melanjutkan.
        </p>
      )}
    </div>
  );
}
