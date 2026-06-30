import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, FileText, CheckCircle, Loader2 } from "lucide-react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

export function UploadArea() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadId, setUploadId] = useState<number | null>(null);
  const [participants, setParticipants] = useState<string[]>([]);
  const [selectedPerson, setSelectedPerson] = useState<string>("");
  const [step, setStep] = useState<"upload" | "select" | "processing">("upload");
  const [platform, setPlatform] = useState<"whatsapp" | "telegram">("whatsapp");
  
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handlePlatformChange = (p: "whatsapp" | "telegram") => {
    setPlatform(p);
    setFile(null);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (selectedFile: File) => {
    const name = selectedFile.name.toLowerCase();
    if (platform === "whatsapp" && !name.endsWith('.txt')) {
      alert("Only WhatsApp chat exports (.txt files) are supported.");
      return;
    }
    if (platform === "telegram" && !name.endsWith('.json')) {
      alert("Only Telegram chat exports (JSON files) are supported.");
      return;
    }
    setFile(selectedFile);
  };

  const startUpload = async () => {
    if (!file) return;
    setUploading(true);
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const res = await axios.post("http://localhost:8000/api/upload", formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 100));
          setProgress(percentCompleted);
        }
      });
      
      if (res.data.upload_id) {
        setUploadId(res.data.upload_id);
        setParticipants(res.data.participants);
        setStep("select");
        setUploading(false);
      }
    } catch (err) {
      console.error(err);
      alert("Upload failed");
      setUploading(false);
    }
  };

  const startProcessing = async () => {
    if (!uploadId || !selectedPerson) return;
    setStep("processing");
    try {
        await axios.post(`http://localhost:8000/api/process/${uploadId}`, { target_person: selectedPerson });
        pollStatus(uploadId);
    } catch(err) {
        console.error(err);
        alert("Processing failed");
        setStep("select");
    }
  };

  const pollStatus = async (id: number) => {
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`http://localhost:8000/api/status/${id}`);
        if (res.data.status === "completed") {
          clearInterval(interval);
          navigate(`/persona/${res.data.persona_id}`);
        } else if (res.data.status.startsWith("failed")) {
          clearInterval(interval);
          alert("Processing failed: " + res.data.status);
          setUploading(false);
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);
  };

  return (
    <div className="w-full max-w-2xl mx-auto mt-12">
      <AnimatePresence mode="wait">
        {step === "upload" && (
          <motion.div
            key="upload-screen"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="flex flex-col gap-6"
          >
            {/* Premium Sliding Segmented Control */}
            <div className="flex justify-center gap-1 p-1 bg-white/5 border border-white/10 rounded-2xl max-w-xs w-full mx-auto backdrop-blur-md">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handlePlatformChange("whatsapp");
                }}
                className={`relative flex-1 py-2.5 px-6 rounded-xl text-sm font-semibold transition-all duration-300 flex items-center justify-center gap-2 ${
                  platform === "whatsapp" ? "text-black" : "text-white/60 hover:text-white"
                }`}
              >
                {platform === "whatsapp" && (
                  <motion.div
                    layoutId="active-platform"
                    className="absolute inset-0 bg-white rounded-xl -z-10"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                WhatsApp
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handlePlatformChange("telegram");
                }}
                className={`relative flex-1 py-2.5 px-6 rounded-xl text-sm font-semibold transition-all duration-300 flex items-center justify-center gap-2 ${
                  platform === "telegram" ? "text-black" : "text-white/60 hover:text-white"
                }`}
              >
                {platform === "telegram" && (
                  <motion.div
                    layoutId="active-platform"
                    className="absolute inset-0 bg-white rounded-xl -z-10"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                Telegram
              </button>
            </div>

            <div
              className={`relative rounded-3xl border-2 border-dashed p-12 transition-all duration-300 ease-in-out flex flex-col items-center justify-center text-center cursor-pointer overflow-hidden backdrop-blur-md bg-white/5 ${
                dragActive 
                  ? "border-primary/50 bg-primary/5 shadow-2xl scale-[1.02]" 
                  : "border-white/10 hover:border-white/20 hover:bg-white/10"
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                accept={platform === "whatsapp" ? ".txt" : ".json"}
                onChange={handleChange}
                className="hidden"
              />
              
              <motion.div
                animate={{ y: dragActive ? -10 : 0 }}
                className="p-4 bg-white/5 rounded-full mb-6"
              >
                <UploadCloud className="w-10 h-10 text-white/60" />
              </motion.div>
              
              <h3 className="text-xl font-semibold mb-2">
                {file ? file.name : `Drop your ${platform === "whatsapp" ? "WhatsApp" : "Telegram"} export here`}
              </h3>
              <p className="text-white/40 mb-8 max-w-sm">
                {file 
                  ? `${(file.size / 1024 / 1024).toFixed(2)} MB` 
                  : platform === "whatsapp"
                    ? "Support for WhatsApp chat exports (.txt files)"
                    : "Support for Telegram chat exports (result.json files)"}
              </p>
              
              {file && (
                <motion.button
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    startUpload();
                  }}
                  className="px-8 py-3 rounded-full bg-white text-black font-semibold hover:bg-white/90 transition-colors shadow-[0_0_20px_rgba(255,255,255,0.3)]"
                >
                  Generate Persona
                </motion.button>
              )}
              
              {uploading && (
                <div className="mt-4 text-white/50">Uploading... {progress}%</div>
              )}
            </div>
          </motion.div>
        )}

        {step === "select" && (
          <motion.div
            key="select-person"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="rounded-3xl border border-white/10 bg-white/5 p-12 flex flex-col items-center justify-center text-center backdrop-blur-md"
          >
            <h3 className="text-2xl font-bold mb-6 bg-gradient-to-r from-white to-white/50 bg-clip-text text-transparent">
              Who are we analyzing?
            </h3>
            <p className="text-white/40 mb-8 max-w-sm">
              Select the person you want to generate a persona for.
            </p>
            
            <div className="flex flex-col gap-4 w-full max-w-xs mb-8">
              {participants.map((p, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedPerson(p)}
                  className={`px-6 py-4 rounded-xl border transition-all ${
                    selectedPerson === p 
                      ? "border-white bg-white text-black font-semibold" 
                      : "border-white/20 bg-black/20 hover:bg-white/10 text-white"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>

            <button
                onClick={startProcessing}
                disabled={!selectedPerson}
                className={`px-8 py-3 rounded-full font-semibold transition-all ${
                  selectedPerson 
                    ? "bg-white text-black hover:bg-white/90 shadow-[0_0_20px_rgba(255,255,255,0.3)] cursor-pointer" 
                    : "bg-white/10 text-white/30 cursor-not-allowed"
                }`}
            >
              Analyze Personality
            </button>
          </motion.div>
        )}

        {step === "processing" && (
          <motion.div
            key="processing"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-3xl border border-white/10 bg-white/5 p-12 flex flex-col items-center justify-center text-center backdrop-blur-md"
          >
            <div className="relative mb-8">
              <Loader2 className="w-16 h-16 text-white animate-spin opacity-20" />
              <div className="absolute inset-0 flex items-center justify-center font-semibold text-xl">
                {progress}%
              </div>
            </div>
            <h3 className="text-2xl font-bold mb-2 bg-gradient-to-r from-white to-white/50 bg-clip-text text-transparent">
              {progress < 100 ? "Uploading chat data..." : "Analyzing personality..."}
            </h3>
            <p className="text-white/40 max-w-sm">
              {progress < 100 
                ? "Securely transferring your export for local processing."
                : "Our AI is reading the messages and extracting deep behavioral insights."}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
