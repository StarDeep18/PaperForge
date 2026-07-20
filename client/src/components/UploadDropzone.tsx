import React, { useState, useRef } from "react";
import { UploadCloud, File, AlertCircle, X, CheckCircle2 } from "lucide-react";

interface UploadDropzoneProps {
  onUpload: (files: File[]) => void;
  isUploading?: boolean;
}

export default function UploadDropzone({
  onUpload,
  isUploading = false,
}: UploadDropzoneProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const allowedExtensions = [".pdf", ".docx", ".txt"];
  const maxBytes = 50 * 1024 * 1024; // 50MB limits

  const validateFiles = (files: File[]): File[] => {
    const valid: File[] = [];
    setErrorMsg(null);

    for (const file of files) {
      const extension = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
      if (!allowedExtensions.includes(extension)) {
        setErrorMsg(`Unsupported file format: ${extension}. Use PDF, DOCX, or TXT.`);
        return [];
      }
      if (file.size > maxBytes) {
        setErrorMsg(`File ${file.name} exceeds the 50MB file size limit.`);
        return [];
      }
      if (file.size === 0) {
        setErrorMsg(`File ${file.name} is empty.`);
        return [];
      }
      valid.push(file);
    }
    return valid;
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
      const files = Array.from(e.dataTransfer.files);
      const valid = validateFiles(files);
      if (valid.length > 0) {
        setSelectedFiles(valid);
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const files = Array.from(e.target.files);
      const valid = validateFiles(files);
      if (valid.length > 0) {
        setSelectedFiles(valid);
      }
    }
  };

  const onButtonClick = () => {
    fileInputRef.current?.click();
  };

  const clearSelection = () => {
    setSelectedFiles([]);
    setErrorMsg(null);
  };

  const handleSubmit = () => {
    if (selectedFiles.length > 0) {
      onUpload(selectedFiles);
      clearSelection();
    }
  };

  return (
    <div className="w-full">
      {/* Dropzone Container */}
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 ${
          dragActive
            ? "border-zinc-900 bg-zinc-50/50 dark:border-zinc-100 dark:bg-zinc-900/30"
            : "border-zinc-200 hover:border-zinc-300 dark:border-zinc-800 dark:hover:border-zinc-700 bg-white dark:bg-zinc-950"
        }`}
        onClick={onButtonClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={handleChange}
          disabled={isUploading}
        />

        <div className="h-12 w-12 rounded-xl bg-zinc-50 dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 flex items-center justify-center mb-4">
          <UploadCloud className="h-6 w-6 text-zinc-500" />
        </div>

        <p className="text-sm font-medium text-zinc-950 dark:text-zinc-50 mb-1">
          Drag & drop research papers here, or click to browse
        </p>
        <p className="text-xs text-zinc-400 dark:text-zinc-500">
          Supports PDF, DOCX, and TXT (Max 50MB)
        </p>
      </div>

      {/* Error Message Box */}
      {errorMsg && (
        <div className="mt-4 p-3 bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 rounded-xl flex items-start gap-2.5 text-xs text-rose-700 dark:text-rose-400">
          <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
          <span className="font-medium">{errorMsg}</span>
        </div>
      )}

      {/* Selected File list & Upload submit triggers */}
      {selectedFiles.length > 0 && (
        <div className="mt-4 border border-zinc-200 dark:border-zinc-800 rounded-xl bg-white dark:bg-zinc-950 p-4">
          <div className="flex items-center justify-between text-xs text-zinc-400 dark:text-zinc-500 mb-3 border-b border-zinc-100 dark:border-zinc-900 pb-2">
            <span>Selected Files ({selectedFiles.length})</span>
            <button
              onClick={clearSelection}
              className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 flex items-center gap-1 cursor-pointer"
            >
              <X className="h-3 w-3" />
              <span>Clear</span>
            </button>
          </div>

          <div className="space-y-2">
            {selectedFiles.map((file, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 text-xs text-zinc-700 dark:text-zinc-300 bg-zinc-50 dark:bg-zinc-900 px-3 py-2 rounded-lg border border-zinc-100 dark:border-zinc-800"
              >
                <File className="h-4 w-4 text-zinc-400" />
                <span className="font-medium truncate flex-1">{file.name}</span>
                <span className="text-[10px] text-zinc-400">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB
                </span>
              </div>
            ))}
          </div>

          <button
            onClick={handleSubmit}
            disabled={isUploading}
            className="w-full mt-4 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-100 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 py-2.5 px-4 rounded-xl text-xs font-semibold tracking-wide transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
          >
            {isUploading ? (
              <>
                <span className="animate-spin h-3.5 w-3.5 border-2 border-zinc-500 border-t-zinc-900 dark:border-zinc-400 dark:border-t-zinc-100 rounded-full" />
                <span>Processing Uploads...</span>
              </>
            ) : (
              <span>Start Document Ingestion</span>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
