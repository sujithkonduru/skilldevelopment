import React from 'react';

export default function ResultsDashboard({ data }) {
  const { transcript, answers, analyses } = data;
  const average =
    analyses.length > 0
      ? analyses.reduce((sum, item) => sum + item.score, 0) / analyses.length
      : 0;

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify({ transcript, answers, analyses }, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'interview_results.json';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">Interview Results</h1>
      <p className="text-lg mb-4">Overall Score: {average.toFixed(1)} / 10</p>

      <div className="space-y-4">
        {answers.map((item, index) => {
          const analysis = analyses[index];
          return (
            <div key={index} className="border rounded p-4">
              <h2 className="text-xl font-semibold">Question {index + 1}</h2>
              <p className="font-medium mt-2">Topic: {item.topic}</p>
              <p className="mt-2">Your Answer: {item.answer || '— skipped —'}</p>
              <p className="mt-2">Score: {analysis.score} / 10</p>
              <div className="mt-2">
                <p className="font-semibold">Strengths</p>
                <ul className="list-disc list-inside">
                  {analysis.strengths.map((s, idx) => (
                    <li key={idx}>{s}</li>
                  ))}
                </ul>
              </div>
              <div className="mt-2">
                <p className="font-semibold">Improvements</p>
                <ul className="list-disc list-inside">
                  {analysis.improvements.map((i, idx) => (
                    <li key={idx}>{i}</li>
                  ))}
                </ul>
              </div>
              <p className="mt-2 font-semibold">Summary</p>
              <p>{analysis.summary}</p>
            </div>
          );
        })}
      </div>

      <button
        type="button"
        className="mt-6 px-4 py-2 bg-blue-600 text-white rounded"
        onClick={downloadJson}
      >
        Download Results (JSON)
      </button>
    </div>
  );
}