const { readFileSync } = require('fs');
const { join } = require('path');

module.exports = async (req, res) => {
  const { message } = req.body;
  const fileDir = join(__dirname, '../public/files');
  const fileList = ['add_questions.py', 'app.py', 'performance.json', 'QBANK_CIA1.csv', 'README.txt'];
  const files = fileList.map(file => {
    try {
      return { name: file, content: readFileSync(join(fileDir, file), 'utf8') };
    } catch (e) {
      return { name: file, content: 'File not found or unreadable' };
    }
  });
  const aiResponse = `You said: "${message}". Files: ${JSON.stringify(files)}. Suggestion: <button>Click me</button>`;
  res.status(200).json({ response: aiResponse });
};