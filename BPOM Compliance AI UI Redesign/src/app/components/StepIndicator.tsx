import { CheckIcon } from "lucide-react";

const steps = [
  { id: 1, label: "Input Dokumen", sublabel: "Upload atau tempel teks" },
  { id: 2, label: "Review Hasil AI", sublabel: "Periksa hasil analisis" },
  { id: 3, label: "Laporan Final", sublabel: "Download laporan PDF" },
];

interface StepIndicatorProps {
  currentStep: number;
}

export function StepIndicator({ currentStep }: StepIndicatorProps) {
  return (
    <div className="w-full bg-white border-b border-border sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-6 py-4">
        <nav aria-label="Progress">
          <ol className="flex items-center justify-center gap-0">
            {steps.map((step, index) => {
              const isCompleted = currentStep > step.id;
              const isActive = currentStep === step.id;
              const isLast = index === steps.length - 1;

              return (
                <li key={step.id} className="flex items-center">
                  <div className="flex flex-col items-center gap-1.5">
                    <div className="flex items-center">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm transition-all duration-200 ${
                          isCompleted
                            ? "bg-[#1E3A5F] text-white"
                            : isActive
                            ? "bg-[#2563EB] text-white ring-4 ring-blue-100"
                            : "bg-slate-100 text-slate-400 border border-slate-200"
                        }`}
                      >
                        {isCompleted ? (
                          <CheckIcon className="w-4 h-4" strokeWidth={2.5} />
                        ) : (
                          <span style={{ fontWeight: 600, fontSize: "13px" }}>{step.id}</span>
                        )}
                      </div>
                    </div>
                    <div className="text-center">
                      <p
                        className={`text-xs transition-colors duration-200 ${
                          isActive
                            ? "text-[#1E3A5F]"
                            : isCompleted
                            ? "text-[#1E3A5F]"
                            : "text-slate-400"
                        }`}
                        style={{ fontWeight: isActive ? 600 : 500 }}
                      >
                        {step.label}
                      </p>
                      <p className="text-[10px] text-slate-400" style={{ display: isActive ? 'block' : 'none' }}>
                        {step.sublabel}
                      </p>
                    </div>
                  </div>

                  {!isLast && (
                    <div
                      className={`h-px w-16 mx-3 mt-[-12px] transition-colors duration-300 ${
                        isCompleted ? "bg-[#1E3A5F]" : "bg-slate-200"
                      }`}
                    />
                  )}
                </li>
              );
            })}
          </ol>
        </nav>
      </div>
    </div>
  );
}
