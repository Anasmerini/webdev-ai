const { readFileSync } = require('fs');
const { join } = require('path');

module.exports = async (req, res) => {
  const { message } = req.body;
  const fileDir = join(__dirname, '../public/files');
  const fileList = ['add_questions.py', 'app.py', 'performance.json', 'QBANK_CIA1.csv', 'README.txt'];

  const files = fileList.map(file => {
    try {
      const content = readFileSync(join(fileDir, file), 'utf8');
      // Summarize: Show first 100 chars or specific data
      let summary = content.slice(0, 100) + (content.length > 100 ? '...' : '');
      if (file === 'QBANK_CIA1.csv' && message.toLowerCase().includes('questions')) {
        const lines = content.split('\n').slice(0, 2); // First question as sample
        summary = lines.join('\n');
      } else if (file === 'performance.json' && message.toLowerCase().includes('performance')) {
        const perf = JSON.parse(content)['Foundations of Internal Auditing'];
        summary = `Correct: ${perf.correct}, Total: ${perf.total}`;
      }
      return { name: file, content: summary };
    } catch (e) {
      return { name: file, content: 'File not found or unreadable' };
    }
  });

  const aiResponse = `You said: "${message}". Files: ${JSON.stringify(files)}. Suggestion: <button>Click me</button>`;
  res.status(200).json({ response: aiResponse });
};