import React, { useState } from 'react';

export default function InterviewSetup({ onComplete }) {
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');

  const handleProcess = () => {
    if (!file) {
      setError('Please select an audio file first.');
      return;
    }
    setError('');
    setIsProcessing(true);

    // Placeholder generation logic for frontend
    const transcript = `Transcribed audio for ${file.name}`;
    const technicalTerms = ['React', 'APIs', 'JavaScript'];
    const questions = technicalTerms.map((term) => ({
      topic: term,
      question: `Explain one important concept about ${term}.`
    }));

    setTimeout(() => {
      onComplete({ transcript, technicalTerms, questions });
      setIsProcessing(false);
    }, 600);
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">AI Technical Interview Assistant</h1>
      <p className="mb-4">
        Upload an audio introduction, then answer generated technical questions.
      </p>

      <div className="mb-4">
        <label className="block font-medium mb-2">Upload audio file</label>
        <input
          type="file"
          accept=".mp3,.wav,.m4a"
          onChange={(e) => setFile(e.target.files[0] || null)}
        />
      </div>

      <button
        type="button"
        className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
        onClick={handleProcess}
        disabled={isProcessing}
      >
        {isProcessing ? 'Processing…' : 'Process Audio'}
      </button>

      {error && <p className="mt-3 text-red-600">{error}</p>}
    </div>
  );
}