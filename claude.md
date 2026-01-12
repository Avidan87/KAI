# Claude Code Guidelines for KAI Project

## Development Principles

### 1. **Think Before Acting** 🧠
- First, thoroughly read the codebase for relevant files
- Understand the problem completely before proposing solutions
- Use Glob, Grep, and Read tools to investigate code

### 2. **Verify Before Major Changes** ✋
- Before making any significant changes, present the plan to the user
- Wait for verification and approval
- Discuss trade-offs and alternatives

### 3. **High-Level Explanations** 📝
- Provide concise, high-level summaries of changes made
- Focus on WHAT changed and WHY, not exhaustive details
- Keep explanations clear and actionable

### 4. **Simplicity First** ⚡
- Make every task and code change as simple as possible
- Avoid massive or complex changes
- Each change should impact as little code as possible
- Prefer targeted edits over large refactors
- Everything is about simplicity

### 5. **Maintain Architecture Documentation** 📚
- Keep the ARCHITECTURE.md file up-to-date
- Document how the app works inside and out
- Update documentation when making architectural changes
- Include diagrams and explanations of key workflows

### 6. **No Speculation - Grounded Answers Only** 🎯
- **NEVER** speculate about code you have not opened
- If the user references a specific file, you **MUST** read it first
- Investigate and read relevant files **BEFORE** answering questions
- Never make claims about code before investigating
- Give grounded, hallucination-free answers based on actual code
- When uncertain, say "Let me read that file first" and use the Read tool

## Code Quality Standards

- ✅ Read files before editing them
- ✅ Test changes when possible
- ✅ Use meaningful variable names
- ✅ Add comments for complex logic
- ✅ Follow existing code patterns
- ✅ Keep functions small and focused
- ✅ Use type hints where applicable

## Communication Style

- Use emojis for better readability (as requested by user)
- Be honest and direct about limitations
- Provide clear explanations of trade-offs
- Ask clarifying questions when requirements are unclear
