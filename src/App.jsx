import React, { useState } from 'react';
import InterviewSetup from './components/InterviewSetup';
import QuestionCard from './components/QuestionCard';
import ResultsDashboard from './components/ResultsDashboard';

function App() {
  const [stage, setStage] = useState('setup');
  const [interviewData, setInterviewData] = useState({
    transcript: '',
    technicalTerms: [],
    questions: [],
    answers: [],
    analyses: [],
    finalReport: null
  });

  const handleSetupComplete = (data) => {
    setInterviewData(prev => ({
      ...prev,
      transcript: data.transcript,
      technicalTerms: data.technicalTerms,
      questions: data.questions
    }));
    setStage('interview');
  };

  const handleAnswerSubmit = (answer, analysis) => {
    setInterviewData(prev => ({
      ...prev,
      answers: [...prev.answers, answer],
      analyses: [...prev.analyses, analysis]
    }));
  };

  const handleInterviewComplete = (finalReport) => {
    setInterviewData(prev => ({
      ...prev,
      finalReport
    }));
    setStage('results');
  };

  return (
    <div className="min-h-screen">
      {stage === 'setup' && <InterviewSetup onComplete={handleSetupComplete} />}
      {stage === 'interview' && (
        <QuestionCard
          questions={interviewData.questions}
          onAnswerSubmit={handleAnswerSubmit}
          onComplete={handleInterviewComplete}
        />
      )}
      {stage === 'results' && <ResultsDashboard data={interviewData} />}
    </div>
  );
}

export default App;