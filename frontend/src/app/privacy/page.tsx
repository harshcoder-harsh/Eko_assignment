import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function PrivacyPolicy() {
  return (
    <main className="min-h-screen bg-[#030303] text-white/80 font-sans p-6 md:p-12 selection:bg-white selection:text-black">
      <div className="max-w-3xl mx-auto">
        <Link href="/" className="inline-flex items-center gap-2 text-white/50 hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>
        
        <h1 className="text-3xl md:text-4xl font-semibold text-white mb-8">Privacy Policy</h1>
        <p className="mb-4 text-white/50">Last updated: {new Date().toLocaleDateString()}</p>
        
        <div className="prose prose-invert prose-white max-w-none space-y-6">
          <section>
            <h2 className="text-xl text-white font-medium mb-3">1. Introduction</h2>
            <p>
              Welcome to Highwatch RAG ("we," "our," or "us"). We are committed to protecting your privacy. This Privacy Policy explains how your personal information and Google Drive data are collected, used, and protected when you use our application.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-white font-medium mb-3">2. Data We Collect</h2>
            <p>When you use our service, we request access to your Google account via OAuth. We specifically request read-only access to your Google Drive.</p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li><strong>Profile Information:</strong> Your email address and basic profile information to create and manage your account.</li>
              <li><strong>Google Drive Files:</strong> We access your PDFs, Word Documents, and Text files strictly for the purpose of analyzing them as requested by you.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl text-white font-medium mb-3">3. How We Use Your Data</h2>
            <p>Your data is used exclusively to provide the core functionality of the application:</p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li><strong>Vectorization:</strong> We extract text from your synced files and convert them into mathematical vectors (embeddings) to enable semantic search.</li>
              <li><strong>AI Processing:</strong> When you ask a question, relevant text chunks from your documents are securely sent to our Large Language Model provider (Groq) to generate an answer. Groq does not use your data to train their models.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl text-white font-medium mb-3">4. Data Storage and Retention</h2>
            <p>
              Your file metadata and chat history are stored securely in a MongoDB database. The vector embeddings of your documents are stored in a local FAISS index. 
              <strong> You have full control over your data.</strong> If you click "Logout & Disconnect" in the application, your local files, OAuth tokens, and session states are immediately deleted from our active server environment.
            </p>
          </section>

          <section>
            <h2 className="text-xl text-white font-medium mb-3">5. Third-Party Sharing</h2>
            <p>
              We do not sell, rent, or share your personal data or document contents with unauthorized third parties. The only third-party services that process your data are:
            </p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li><strong>Groq:</strong> Used strictly as an API for AI inference.</li>
              <li><strong>MongoDB Atlas:</strong> Used strictly for secure cloud database hosting.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl text-white font-medium mb-3">6. Google API Services User Data Policy</h2>
            <p>
              Highwatch RAG's use and transfer to any other app of information received from Google APIs will adhere to the <a href="https://developers.google.com/terms/api-services-user-data-policy" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">Google API Services User Data Policy</a>, including the Limited Use requirements.
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}