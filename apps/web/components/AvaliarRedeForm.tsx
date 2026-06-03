"use client";

import { useState } from "react";
import {
  Upload,
  Download,
  Loader2,
  FileSpreadsheet,
  AlertCircle,
} from "lucide-react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { downloadBatchCsvTemplate, uploadBatchCsv } from "@/lib/api";

const MAX_LOJAS = 50;

export function AvaliarRedeForm() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleDownloadTemplate() {
    setError(null);
    setDownloadingTemplate(true);
    try {
      const supabase = createSupabaseBrowserClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        setError("Sessão expirada — recarregue a página");
        return;
      }
      await downloadBatchCsvTemplate(session.access_token);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`Falha ao baixar template: ${msg}`);
    } finally {
      setDownloadingTemplate(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    if (!file) {
      setError("Selecione um arquivo CSV");
      return;
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Apenas arquivos .csv são aceitos");
      return;
    }

    if (file.size > 1_000_000) {
      setError("Arquivo grande demais (>1 MB)");
      return;
    }

    setUploading(true);
    try {
      const supabase = createSupabaseBrowserClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        setError("Sessão expirada — recarregue a página");
        return;
      }
      await uploadBatchCsv(session.access_token, file);
      setSuccess(
        `Avaliação consolidada baixada com sucesso. Cada loja também foi salva no seu histórico.`,
      );
      setFile(null);
      // Limpa input visual
      const input = document.getElementById("csv-input") as HTMLInputElement | null;
      if (input) input.value = "";
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Como funciona */}
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-mudacao-950">Como funciona</h2>
        <ol className="mt-3 space-y-2 text-sm text-slate-700">
          <li>
            <strong>1.</strong> Baixe o template CSV (1 linha por loja, com 15
            colunas).
          </li>
          <li>
            <strong>2.</strong> Preencha até <strong>{MAX_LOJAS} lojas</strong>{" "}
            no Excel/Sheets e salve como CSV.
          </li>
          <li>
            <strong>3.</strong> Suba o arquivo aqui. A gente roda a simulação
            de cada loja e devolve um <strong>.xlsx consolidado</strong> com
            resumo da rede + detalhes por loja.
          </li>
          <li>
            <strong>4.</strong> Cada simulação também entra no seu histórico
            individualmente.
          </li>
        </ol>

        <div className="mt-5">
          <button
            type="button"
            onClick={handleDownloadTemplate}
            disabled={downloadingTemplate}
            className="inline-flex items-center gap-2 rounded-lg border border-mudacao-300 bg-mudacao-50 px-4 py-2 text-sm font-medium text-mudacao-900 hover:bg-mudacao-100 disabled:opacity-50"
          >
            {downloadingTemplate ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Baixando…
              </>
            ) : (
              <>
                <Download className="h-4 w-4" />
                Baixar template CSV
              </>
            )}
          </button>
        </div>
      </div>

      {/* Form upload */}
      <form
        onSubmit={handleSubmit}
        className="rounded-xl border border-slate-200 bg-white p-6"
      >
        <h2 className="text-lg font-semibold text-mudacao-950">
          Subir CSV da rede
        </h2>
        <p className="mt-1 text-sm text-slate-600">
          Limite: {MAX_LOJAS} lojas e 1 MB por upload. Processamento síncrono
          (pode levar até ~10s).
        </p>

        <div className="mt-5">
          <label
            htmlFor="csv-input"
            className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center transition hover:border-mudacao-300 hover:bg-mudacao-50"
          >
            <FileSpreadsheet className="h-10 w-10 text-slate-400" />
            <p className="mt-2 text-sm font-medium text-slate-700">
              {file ? file.name : "Clique pra selecionar o CSV"}
            </p>
            {file ? (
              <p className="mt-1 text-xs text-slate-500">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            ) : (
              <p className="mt-1 text-xs text-slate-500">
                Arquivos .csv até 1 MB
              </p>
            )}
            <input
              id="csv-input"
              type="file"
              accept=".csv,text/csv"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              disabled={uploading}
            />
          </label>
        </div>

        {error && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="mt-4 rounded-lg border border-mudacao-200 bg-mudacao-50 p-3 text-sm text-mudacao-900">
            {success}
          </div>
        )}

        <button
          type="submit"
          disabled={uploading || !file}
          className="btn-primary mt-5 w-full"
        >
          {uploading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Processando rede…
            </>
          ) : (
            <>
              <Upload className="h-5 w-5" />
              Avaliar rede e baixar Excel
            </>
          )}
        </button>
      </form>

      <p className="text-center text-xs text-slate-500">
        Cada loja é simulada individualmente. Resultado pode demorar alguns
        segundos pra redes maiores.
      </p>
    </div>
  );
}
