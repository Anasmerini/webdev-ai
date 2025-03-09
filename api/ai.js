module.exports = async (req, res) => {
  const { message } = req.body;
  const aiResponse = `You said: "${message}". Here's a suggestion: <button>Click me</button>`;
  res.status(200).json({ response: aiResponse });
}; 
