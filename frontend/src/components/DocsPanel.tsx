"use client";

import { motion } from "framer-motion";
import { FileText, CheckCircle, Database } from "lucide-react";

export function DocsPanel({ docs, onDocumentClick }: { docs: { id: string, name: string, status: string }[], onDocumentClick?: (doc: { id: string, name: string }) => void }) {
  return (
    <div className="flex-1 overflow-y-auto pr-1 -mr-1 space-y-1.5 custom-scrollbar">
      {docs.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-32 text-white/30 gap-3">
          <Database className="w-6 h-6 opacity-50" />
          <p className="text-xs">No documents synced.</p>
        </div>
      ) : (
        docs.map((doc, idx) => (
          <motion.div 
            key={`${doc.id}-${idx}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.03 }}
            onClick={() => onDocumentClick && onDocumentClick({ id: doc.id, name: doc.name })}
            className="p-2.5 rounded-lg flex items-center gap-3 group/item hover:bg-white/[0.08] transition-colors cursor-pointer active:scale-[0.98]"
            title="Click to ask AI to summarize this document"
          >
            <div className="w-7 h-7 rounded-md bg-white/[0.05] flex items-center justify-center transition-colors border border-white/[0.05]">
              {doc.status === "Indexed" ? (
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <FileText className="w-3.5 h-3.5 text-white/50 group-hover/item:text-white" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate text-white/70 group-hover/item:text-white transition-colors">{doc.name}</p>
            </div>
          </motion.div>
        ))
      )}
    </div>
  );
}
