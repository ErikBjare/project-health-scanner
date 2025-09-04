# 🏥 Project Health Scanner

A comprehensive tool to monitor and analyze the health of all your development projects. Get instant insights into project status, dependencies, GitHub activity, code quality metrics, and more!

## ✨ Features

- **🔍 Automatic Project Discovery** - Scans directories for git repositories
- **📊 Comprehensive Health Scoring** - 0-10 scale based on multiple metrics
- **🐙 GitHub Integration** - Issues, PRs, stars, and activity tracking
- **📦 Dependency Analysis** - Supports npm, pip, poetry, go modules
- **🧪 Quality Metrics** - Documentation, testing, CI/CD, code quality tools
- **💻 Multi-Language Support** - Python, JavaScript, TypeScript, Go, Rust, and more
- **📈 Interactive Dashboard** - Beautiful HTML reports with charts
- **⚡ Lightning Fast** - Efficient scanning with smart timeouts

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/ErikBjare/project-health-scanner.git
cd project-health-scanner

# Run a quick analysis
python main.py --scan ~/Programming --analyze-only

# Generate HTML report
python main.py --scan ~/Programming --output-html report.html
```

## 📋 Installation

### Requirements
- Python 3.10+
- Git repositories to analyze

### Dependencies
```bash
pip install -r requirements.txt
```

No external dependencies required! Uses only Python standard library.

## 🎯 Usage

### Basic Analysis
```bash
# Analyze projects in current directory
python main.py --analyze-only

# Analyze specific directory
python main.py --scan /path/to/projects --analyze-only

# Include GitHub metrics (optional token for higher rate limits)
python main.py --scan ~/Programming --github-token YOUR_TOKEN --analyze-only
```

### Generate Reports
```bash
# Static HTML report
python main.py --scan ~/Programming --output-html health-report.html

# Live web dashboard
python main.py --scan ~/Programming --port 8080
```

## 📊 Health Scoring

Projects are scored on a 0-10 scale based on multiple factors:

### Git Health (Base: 10.0)
- **Uncommitted Changes**: -3.0 for >50, -2.0 for >10, -0.1 per change for <10
- **Commit Age**: -4.0 for >1 year, -2.5 for >6 months, -1.5 for >2 months
- **Remote Status**: -0.5 for unknown remote

### Dependencies (+0.8)
- **Has Dependencies**: +0.5 (indicates active project)
- **Reasonable Count**: +0.3 for 5-50 deps, -0.5 for >100 deps
- **Multi-Language**: +0.2 for polyglot projects

### GitHub Metrics (+1.1)
- **Issues**: -1.5 for >50, -1.0 for >20, -0.5 for >10
- **Pull Requests**: +0.3 for 1-5, -0.3 for >10
- **Stars**: +0.5 for >1000, +0.3 for >100, +0.1 for >10
- **Recent Activity**: +0.2 for activity within 7 days

### Quality Metrics (+3.8)
- **README**: +0.4-0.8 based on quality
- **Documentation**: +0.4 for docs/ directory
- **Testing**: +0.6-1.0 based on test coverage
- **CI/CD**: +0.6 for automated pipelines
- **Code Quality Tools**: +0.1 per tool (max +0.5)
- **Project Structure**: +0.1-0.5 for organization

### Example Scores
- **10.0/10**: Perfect project (gptme) - Recent commits, comprehensive docs, tests, CI/CD
- **9.0-9.9**: Excellent projects - Minor issues or missing features
- **8.0-8.9**: Healthy projects - Generally well-maintained
- **5.0-7.9**: Warning - Needs attention
- **0.0-4.9**: Unhealthy - Requires significant maintenance

## 📈 Output Examples

### Text Analysis

### Text Analysis
✅ gptme (10.0/10)
   📂 /Users/user/Programming/gptme
   🌿 Branch: master
   📅 Last commit: 2025-09-03 (0 days ago)
   📝 Uncommitted changes: 22
   💻 Languages: Python, TypeScript, CSS, HTML, Vue
   📦 Dependencies: poetry: 39 deps, 29 dev deps
   🐙 GitHub: gptme/gptme
   ⭐ Stars: 3986
   🐛 Issues: 81 | 🔄 PRs: 30

📊 Analysis Complete!
   Total projects: 117
   Healthy (8-10): 33
   Warning (5-8): 77
   Unhealthy (0-5): 7

### HTML Dashboard
The HTML output includes:
- 📊 Interactive charts with Chart.js
- 🎨 Clean, responsive design
- 📱 Mobile-friendly interface
- 🔗 Direct GitHub repository links
- ⚡ Real-time project filtering

## 🔧 Command Line Options

```bash
python main.py [OPTIONS]

Options:
  --scan DIRECTORY          Directory to scan (default: ~/Programming)
  --analyze-only            Text output only, no server
  --output-html FILENAME    Generate static HTML report
  --github-token TOKEN      GitHub API token (optional)
  --port PORT              Server port (default: 8042)
  --no-browser             Don't open browser automatically
```

## 🛠️ Supported Technologies

### Languages
Python, JavaScript, TypeScript, Go, Rust, Java, C++, C, HTML, CSS, Vue, PHP, Ruby, Swift, Kotlin

### Package Managers
- **Node.js**: package.json (npm/yarn)
- **Python**: requirements.txt, pyproject.toml (poetry)
- **Go**: go.mod
- **Rust**: Cargo.toml (coming soon)
- **PHP**: composer.json (coming soon)

### CI/CD Platforms
GitHub Actions, GitLab CI, Travis CI, Azure Pipelines, Jenkins, CircleCI

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

Built with gptme - the powerful AI assistant for developers.
