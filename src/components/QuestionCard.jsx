import React, { useState } from 'react';

function buildAnalysis(answer) {
  const trimmed = answer.trim();
  const score = Math.min(10, Math.max(3, Math.floor(trimmed.length / 20)));
  return {
    score,
    strengths: ['Clear structure', 'Relevant examples'],
    improvements: ['Add more detail', 'Use precise terminology'],
    missing_points: ['Include edge cases', 'Mention performance implications'],
    summary: 'Good start; expand and clarify the answer for a stronger response.'
  };
}

export default function QuestionCard({ questions, onAnswerSubmit, onComplete }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');

  const currentQuestion = questions[currentIndex];

  const handleSubmit = () => {
    if (!answer.trim()) {
      setError('Please enter your answer before submitting.');
      return;
    }
    setError('');
    const analysis = buildAnalysis(answer);
    onAnswerSubmit(answer, analysis);
    setAnswer('');

    if (currentIndex + 1 >= questions.length) {
      onComplete({ report: 'Interview complete' });
    } else {
      setCurrentIndex((prev) => prev + 1);
    }
  };

  const handleSkip = () => {
    const skippedAnalysis = {
      score: 0,
      strengths: [],
      improvements: ['Skipped question'],
      missing_points: ['No answer provided'],
      summary: 'Question skipped.'
    };
    onAnswerSubmit('', skippedAnalysis);
    setAnswer('');
    if (currentIndex + 1 >= questions.length) {
      onComplete({ report: 'Interview complete' });
    } else {
      setCurrentIndex((prev) => prev + 1);
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-4">
        <p className="text-sm text-gray-600">
          Question {currentIndex + 1} of {questions.length}
        </p>
        <h2 className="text-xl font-semibold mt-2">{currentQuestion.topic}</h2>
        <p className="mt-2">{currentQuestion.question}</p>
      </div>

      <textarea
        className="w-full p-3 border rounded mb-3"
        rows="8"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
      />

      {error && <p className="text-red-600 mb-3">{error}</p>}

      <div className="flex gap-3">
        <button
          type="button"
          className="px-4 py-2 bg-blue-600 text-white rounded"
          onClick={handleSubmit}
        >
          Submit Answer
        </button>
        <button
          type="button"
          className="px-4 py-2 bg-gray-200 rounded"
          onClick={handleSkip}
        >
          Skip Question
        </button>
      </div>
    </div>
  );
}