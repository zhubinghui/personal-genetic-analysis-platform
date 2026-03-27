"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { sampleApi, ApiError } from "@/lib/api";

type ArrayType = "EPIC" | "450K";

export default function UploadPage() {
  const router = useRouter();
  const [uploadMode, setUploadMode] = useState<"idat" | "csv">("idat");
  const [arrayType, setArrayType] = useState<ArrayType>("EPIC");
  const [age, setAge] = useState<string>("");
  const [redFile, setRedFile] = useState<File | null>(null);
  const [grnFile, setGrnFile] = useState<File | null>(null);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onDropIdat = useCallback((acceptedFiles: File[]) => {
    acceptedFiles.forEach((f) => {
      if (f.name.includes("_Red") || f.name.toLowerCase().endsWith("red.idat")) {
        setRedFile(f);
      } else {
        setGrnFile(f);
      }
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: uploadMode === "idat" ? onDropIdat : (files) => setCsvFile(files[0]),
    accept: uploadMode === "idat" ? { "application/octet-stream": [".idat"] } : { "text/csv": [".csv"] },
    multiple: uploadMode === "idat",
  });

  const handleUpload = async () => {
    const chronAge = parseInt(age);
    if (!chronAge || chronAge < 1 || chronAge > 120) {
      setError("请填写有效年龄（1-120）");
      return;
    }
    if (uploadMode === "idat" && (!redFile || !grnFile)) {
      setError("请上传 Red 和 Grn IDAT 文件");
      return;
    }
    if (uploadMode === "csv" && !csvFile) {
      setError("请上传 beta 值矩阵 CSV 文件");
      return;
    }

    setLoading(true);
    setError("");
    try {
      let result;
      if (uploadMode === "idat") {
        result = await sampleApi.uploadIdat(redFile!, grnFile!, arrayType, chronAge);
      } else {
        result = await sampleApi.uploadBetaCsv(csvFile!, arrayType, chronAge);
      }
      router.push(`/results/${result.job_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "上传失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold text-gray-800">上传甲基化数据</h1>

        {/* 上传模式 */}
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <div className="flex gap-3">
            {(["idat", "csv"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setUploadMode(mode)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  uploadMode === mode
                    ? "bg-brand-600 text-white"
                    : "border border-gray-300 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {mode === "idat" ? "IDAT 文件（原始芯片数据）" : "Beta 值矩阵 CSV"}
              </button>
            ))}
          </div>

          {/* 芯片类型 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">芯片类型</label>
            <select
              value={arrayType}
              onChange={(e) => setArrayType(e.target.value as ArrayType)}
              className="border rounded-lg px-3 py-2 text-sm"
            >
              <option value="EPIC">Illumina EPIC（850K）</option>
              <option value="450K">Illumina 450K</option>
            </select>
          </div>

          {/* 年龄 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">实际年龄（岁）</label>
            <input
              type="number" min={1} max={120} value={age}
              onChange={(e) => setAge(e.target.value)}
              placeholder="例：45"
              className="border rounded-lg px-3 py-2 text-sm w-32"
            />
          </div>
        </div>

        {/* 文件拖拽区 */}
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition ${
            isDragActive ? "border-brand-500 bg-brand-50" : "border-gray-300 hover:border-brand-400"
          }`}
        >
          <input {...getInputProps()} />
          <p className="text-gray-500">
            {isDragActive
              ? "释放文件..."
              : uploadMode === "idat"
              ? "拖拽 IDAT 文件（Red + Grn）到此处，或点击选择"
              : "拖拽 beta 值矩阵 CSV 到此处，或点击选择"}
          </p>
          {uploadMode === "idat" && (
            <div className="mt-3 space-y-1 text-sm">
              {redFile && <p className="text-green-600">✓ Red: {redFile.name}</p>}
              {grnFile && <p className="text-green-600">✓ Grn: {grnFile.name}</p>}
            </div>
          )}
          {uploadMode === "csv" && csvFile && (
            <p className="mt-3 text-sm text-green-600">✓ {csvFile.name}</p>
          )}
        </div>

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button
          onClick={handleUpload}
          disabled={loading}
          className="w-full bg-brand-600 text-white py-3 rounded-xl font-medium hover:bg-brand-700 disabled:opacity-50 transition"
        >
          {loading ? "上传并分析中..." : "开始分析"}
        </button>

        <p className="text-xs text-gray-400 text-center">
          文件使用 AES-256-GCM 加密后存储。分析通常需要 5-20 分钟。
        </p>
      </div>
    </div>
  );
}
