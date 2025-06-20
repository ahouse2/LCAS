# LCAS_2 - Restructured Legal Case Analysis System

# LCAS v4.0 - Legal Case Analysis System

🚀 **A comprehensive, modular system for organizing and analyzing legal evidence with AI-powered insights.**

## Overview

LCAS (Legal Case Analysis System) is designed to help legal professionals organize, analyze, and present evidence for court cases. Built with a modular plugin architecture, it provides:

- **Intelligent Evidence Organization**: Automatically categorizes files into legal argument folders
- **File Integrity Verification**: Generates cryptographic hashes for evidence preservation
- **AI-Powered Analysis**: Optional integration with multiple AI providers
- **Professional Reporting**: Comprehensive analysis reports for case presentation
- **Extensible Framework**: Easy plugin development for custom functionality

## 🏗️ Architecture

LCAS v4.0 uses a modular plugin architecture:

```
LCAS/
├── lcas/
│   ├── core.py              # Core application engine
│   ├── main.py              # Main CLI entry point
│   ├── gui.py               # GUI interface
│   ├── cli.py               # Command-line interface
│   ├── utils.py             # Utility functions
│   └── plugins/             # Plugin system
├── plugins/                 # Independent analysis plugins
├── config/                  # Configuration templates
├── docs/                    # Documentation
└── tests/                   # Test suite
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- pip package manager

### Installation

1. **Install from PyPI (recommended):**
   ```bash
   pip install lcas
   ```

2. **Or install from source:**
   ```bash
   git clone https://github.com/ahouse2/LCAS.git
   cd LCAS
   pip install -e .
   ```

3. **Install optional dependencies:**
   ```bash
   # For AI features
   pip install lcas[ai]

   # For advanced NLP
   pip install lcas[advanced]

   # For enhanced GUI
   pip install lcas[gui]

   # For development
   pip install lcas[dev]
   ```

### Basic Usage

#### GUI Interface
```bash
lcas-gui
```

#### Command Line Interface
```bash
# Interactive configuration
lcas-cli config

# Quick analysis
lcas-cli quick /path/to/evidence /path/to/results --case-name "My Case"

# Full analysis with configuration file
lcas-cli analyze --config my_config.json
```

#### Python API
```python
from lcas import LCASCore, LCASConfig

# Create configuration
config = LCASConfig(
    case_name="My Legal Case",
    source_directory="/path/to/evidence",
    target_directory="/path/to/results"
)

# Initialize and run analysis
core = LCASCore(config)
await core.initialize()

# Analysis will be performed by loaded plugins
```

## 📁 Folder Structure

LCAS organizes evidence into a standardized legal argument structure:

```
YOUR_CASE/
├── 00_ORIGINAL_FILES_BACKUP/          # Preserved original files
├── 01_CASE_SUMMARIES_AND_RELATED_DOCS/ # Case summaries, pleadings
├── 02_CONSTITUTIONAL_VIOLATIONS/       # Due process violations
├── 03_ELECTRONIC_ABUSE/                # Digital surveillance evidence
├── 04_FRAUD_ON_THE_COURT/             # Court fraud evidence
├── 05_NON_DISCLOSURE_FC2107_FC2122/   # Financial disclosure violations
├── 06_PD065288_COURT_RECORD_DOCS/     # Court records
├── 07_POST_TRIAL_ABUSE/               # Post-trial violations
├── 08_TEXT_MESSAGES/                  # Communication evidence
├── 09_FOR_HUMAN_REVIEW/               # Uncategorized files
└── 10_VISUALIZATIONS_AND_REPORTS/     # Generated reports
```

## 🔌 Plugin System

LCAS uses a modular plugin architecture. Available plugins include:

### Core Plugins
- **File Ingestion**: Preserves original files and creates working copies
- **Evidence Categorization**: Sorts files into legal argument folders
- **Hash Generation**: Creates SHA256 hashes for file integrity
- **Timeline Analysis**: Builds chronological evidence timelines
- **Report Generation**: Produces comprehensive analysis reports

### Advanced Plugins
- **AI Integration**: AI-powered document analysis
- **Pattern Discovery**: Identifies relationships between evidence
- **Image Analysis**: Processes visual evidence

## ⚙️ Configuration

### Configuration File (JSON)
```json
{
  "case_name": "Your Case Name",
  "source_directory": "/path/to/evidence",
  "target_directory": "/path/to/results",
  "enabled_plugins": [
    "file_ingestion_plugin",
    "evidence_categorization_plugin",
    "hash_generation_plugin"
  ],
  "debug_mode": false,
  "log_level": "INFO"
}
```

### Environment Variables
```bash
export LCAS_CONFIG_PATH="/path/to/config.json"
export LCAS_LOG_LEVEL="DEBUG"
export OPENAI_API_KEY="your-api-key"  # For AI features
```

## 🤖 AI Integration

LCAS supports multiple AI providers for enhanced analysis:

- **OpenAI**: GPT models for document analysis
- **Anthropic**: Claude for legal reasoning
- **Local Models**: Self-hosted solutions

Enable AI features:
```bash
pip install lcas[ai]
```

Configure in your config file:
```json
{
  "ai_config": {
    "provider": "openai",
    "model": "gpt-4",
    "api_key": "your-api-key",
    "enabled": true
  }
}
```

### Detailed AI Configuration (`config/ai_config.json`)

While the main `lcas_config.json` can enable the AI plugin, the detailed configuration for AI providers (OpenAI, Anthropic, local models) and their behavior is managed in a separate file: `config/ai_config.json`.

**Important:**
- If this file does not exist when LCAS starts with the AI plugin enabled, it will be automatically created in your project's `config/` directory with default settings and **empty placeholders for API keys**.
- **You MUST edit `config/ai_config.json` to add your valid API keys** for services like OpenAI or Anthropic. You also need to configure the endpoint if you are using a local AI model. Without these, the AI functionalities will not work.
- This file also allows for advanced customization of AI behavior, such as selecting preferred models, setting analysis depth, configuring rate limits, and more. Refer to the comments or documentation within `config/ai_config.json` for more details once it's generated.

## 📊 Use Cases

### Legal Professionals
- **Discovery Phase**: Organize thousands of documents efficiently
- **Case Preparation**: Categorize evidence by legal arguments
- **Expert Testimony**: Generate integrity reports with cryptographic hashes
- **Appeal Preparation**: Systematic evidence review and analysis

### Litigation Support
- **Document Review**: Automated categorization and scoring
- **Evidence Mapping**: Visual relationship analysis
- **Timeline Construction**: Chronological evidence organization
- **Quality Assurance**: File integrity verification

## 🛠️ Development

### Setting up Development Environment
```bash
git clone https://github.com/ahouse2/LCAS.git
cd LCAS
pip install -e .[dev]
```

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black lcas/
isort lcas/
```

### Creating a Plugin
```python
from lcas.core import AnalysisPlugin

class MyCustomPlugin(AnalysisPlugin):
    @property
    def name(self) -> str:
        return "My Custom Plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Custom analysis functionality"

    @property
    def dependencies(self) -> List[str]:
        return []

    async def initialize(self, core_app) -> bool:
        self.core = core_app
        return True

    async def cleanup(self) -> None:
        pass

    async def analyze(self, data) -> Dict[str, Any]:
        # Your analysis logic here
        return {"status": "completed"}
```

## 🏆 Key Features

### Evidence Organization
- ✅ Automated file categorization
- ✅ Preserves original file integrity
- ✅ Handles duplicate files intelligently
- ✅ Creates searchable folder structure

### Analysis & Scoring
- ✅ Evidence relevance scoring
- ✅ Admissibility likelihood assessment
- ✅ Pattern discovery across documents
- ✅ Timeline analysis

### Professional Reporting
- ✅ Comprehensive analysis reports
- ✅ Visual relationship graphs
- ✅ Evidence integrity documentation
- ✅ Case presentation materials

### Technical Features
- ✅ Modular plugin architecture
- ✅ Asynchronous processing
- ✅ Cross-platform compatibility
- ✅ Professional GUI and CLI interfaces

## 🔒 Security & Integrity

LCAS prioritizes evidence integrity:

- **Original Preservation**: Never modifies source files
- **Cryptographic Hashing**: SHA256 verification for all files
- **Chain of Custody**: Detailed processing logs
- **Backup Systems**: Multiple preservation strategies

## 📚 Documentation

- **User Guide**: Complete usage instructions
- **Plugin Development**: Create custom analysis tools
- **API Reference**: Technical implementation details
- **Legal Guidelines**: Best practices for evidence handling

## 🤝 Contributing

Contributions welcome! Areas of focus:

- **New Plugins**: Analysis algorithms and specialized tools
- **AI Integration**: Enhanced language model capabilities
- **Visualization**: Advanced reporting and graphics
- **Legal Research**: Integration with legal databases

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/ahouse2/LCAS/issues)
- **Documentation**: See `docs/` directory
- **Discussions**: [GitHub Discussions](https://github.com/ahouse2/LCAS/discussions)

## 🎯 Roadmap

### Version 4.1 (Planned)
- [ ] Enhanced AI integration with multiple providers
- [ ] Real-time collaboration features
- [ ] Cloud storage integration
- [ ] Advanced visualization tools

### Version 4.2 (Future)
- [ ] Mobile companion app
- [ ] Integration with legal databases
- [ ] Advanced machine learning models
- [ ] Multi-language support

---

**Built for legal professionals who demand precision, efficiency, and reliability in evidence analysis.**

*LCAS v4.0 - Where legal expertise meets cutting-edge technology.*
