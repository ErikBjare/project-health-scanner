#!/usr/bin/env python3
"""
Project Health Scanner - Monitor the health of all your development projects
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import webbrowser
import http.server
import socketserver
from threading import Thread
import time
import urllib.parse
import urllib.request

@dataclass
class ProjectHealth:
    """Represents the health status of a single project"""
    name: str
    path: str
    git_status: str
    last_commit: Optional[datetime]
    uncommitted_changes: int
    branch: str
    remote_status: str
    languages: List[str]
    dependencies_status: str
    issues_count: int
    health_score: float
    # GitHub integration
    github_repo: Optional[str] = None
    open_issues: int = 0
    open_prs: int = 0
    stars: int = 0
    workflow_status: str = "unknown"
    last_github_activity: Optional[datetime] = None

class ProjectScanner:
    """Scans directories for development projects and analyzes their health"""
    
    def __init__(self, base_path: str, github_token: Optional[str] = None):
        self.base_path = Path(base_path).expanduser()
        self.projects: List[ProjectHealth] = []
        self.github_token = github_token
    
    def scan_projects(self) -> List[ProjectHealth]:
        """Scan base directory for all development projects"""
        print(f"🔍 Scanning projects in {self.base_path}")
        
        # First check if the base directory itself is a git repository
        if (self.base_path / '.git').exists():
            try:
                health = self._analyze_project(self.base_path)
                if health:
                    self.projects.append(health)
                    print(f"  ✅ {health.name} (Score: {health.health_score:.1f}/10)")
            except Exception as e:
                print(f"  ❌ Error analyzing {self.base_path.name}: {e}")
        
        # Then scan subdirectories
        for item in self.base_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                try:
                    health = self._analyze_project(item)
                    if health:
                        self.projects.append(health)
                        print(f"  ✅ {health.name} (Score: {health.health_score:.1f}/10)")
                    else:
                        print(f"  ⏭️  Skipped {item.name}")
                except Exception as e:
                    print(f"  ❌ Error analyzing {item.name}: {e}")
        
        return self.projects
    
    def _analyze_project(self, project_path: Path) -> Optional[ProjectHealth]:
        """Analyze a single project for health metrics"""
        
        # Check if it's a git repository
        if not (project_path / '.git').exists():
            return None
        
        try:
            # Get git information
            git_info = self._get_git_info(project_path)
            if not git_info:
                return None
            
            # Detect languages
            languages = self._detect_languages(project_path)
            
            # Check dependencies
            dep_info = self._check_dependencies(project_path)
            
            # Get GitHub information
            github_repo = self._get_github_repo(project_path)
            github_info = {
                'stars': 0,
                'open_issues': 0,
                'open_prs': 0,
                'last_activity': None,
                'workflow_status': 'unknown'
            }
            
            if github_repo and hasattr(self, 'github_token'):
                github_info = self._fetch_github_info(github_repo, self.github_token)
            
            # Check additional quality metrics
            quality_info = self._check_project_quality(project_path)
            
            # Calculate health score (including all metrics)
            health_score = self._calculate_health_score(git_info, dep_info, github_info, quality_info)
            
            # Format dependency status for display
            if dep_info['has_deps']:
                dep_display = ', '.join(dep_info['details'])
            else:
                dep_display = 'No dependencies found'
            
            return ProjectHealth(
                name=project_path.name,
                path=str(project_path),
                git_status=git_info['status'],
                last_commit=git_info['last_commit'],
                uncommitted_changes=git_info['uncommitted'],
                branch=git_info['branch'],
                remote_status=git_info['remote_status'],
                languages=languages,
                dependencies_status=dep_display,
                issues_count=github_info['open_issues'],
                health_score=health_score,
                github_repo=github_repo,
                open_issues=github_info['open_issues'],
                open_prs=github_info['open_prs'],
                stars=github_info['stars'],
                workflow_status=github_info['workflow_status'],
                last_github_activity=github_info['last_activity']
            )
            
        except Exception as e:
            print(f"  ⚠️  Error analyzing {project_path.name}: {e}")
            return None
    
    def _get_git_info(self, project_path: Path) -> Optional[Dict]:
        """Extract git information from project"""
        original_cwd = os.getcwd()
        try:
            os.chdir(project_path)
            
            # Get current branch with timeout
            branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                         capture_output=True, text=True, timeout=5)
            if branch_result.returncode != 0:
                return None
            branch = branch_result.stdout.strip() or 'main'
            
            # Get last commit date with timeout  
            commit_result = subprocess.run(['git', 'log', '-1', '--format=%ci'], 
                                         capture_output=True, text=True, timeout=5)
            if commit_result.returncode != 0:
                return None
                
            last_commit = None
            if commit_result.stdout.strip():
                try:
                    commit_date = commit_result.stdout.strip()
                    # Handle timezone format more robustly
                    if '+' in commit_date:
                        commit_date = commit_date.split('+')[0].strip()
                    last_commit = datetime.fromisoformat(commit_date.replace(' ', 'T'))
                except Exception:
                    # If we can't parse the date, just skip it
                    pass
            
            # Check for uncommitted changes with timeout
            status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                         capture_output=True, text=True, timeout=5)
            if status_result.returncode != 0:
                return None
            uncommitted = len([line for line in status_result.stdout.strip().split('\n') 
                             if line.strip()]) if status_result.stdout.strip() else 0
            
            return {
                'branch': branch,
                'last_commit': last_commit,
                'uncommitted': uncommitted,
                'status': 'clean' if uncommitted == 0 else 'dirty',
                'remote_status': 'unknown'
            }
            
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None
        finally:
            # Always restore original directory
            try:
                os.chdir(original_cwd)
            except Exception:
                pass
    
    def _detect_languages(self, project_path: Path) -> List[str]:
        """Detect programming languages used in the project"""
        language_extensions = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.go': 'Go',
            '.rs': 'Rust',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.html': 'HTML',
            '.css': 'CSS',
            '.vue': 'Vue',
            '.php': 'PHP',
            '.rb': 'Ruby',
            '.swift': 'Swift',
            '.kt': 'Kotlin'
        }
        
        languages = set()
        for file_path in project_path.rglob('*'):
            if file_path.is_file() and file_path.suffix in language_extensions:
                languages.add(language_extensions[file_path.suffix])
                if len(languages) >= 5:  # Limit to top 5 languages
                    break
        
        return list(languages)
    
    def _check_dependencies(self, project_path: Path) -> Dict:
        """Check dependency health for the project"""
        dep_info = {
            'has_deps': False,
            'languages': [],
            'dep_counts': {},
            'details': []
        }
        
        # Check package.json for Node.js
        package_json = project_path / 'package.json'
        if package_json.exists():
            try:
                import json
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    deps = len(data.get('dependencies', {}))
                    dev_deps = len(data.get('devDependencies', {}))
                    dep_info['has_deps'] = True
                    dep_info['languages'].append('Node.js')
                    dep_info['dep_counts']['npm'] = deps + dev_deps
                    dep_info['details'].append(f"npm: {deps} deps, {dev_deps} dev deps")
            except Exception:
                pass
        
        # Check requirements.txt for Python
        req_txt = project_path / 'requirements.txt'
        if req_txt.exists():
            try:
                with open(req_txt, 'r') as f:
                    lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    dep_count = len(lines)
                    dep_info['has_deps'] = True
                    dep_info['languages'].append('Python')
                    dep_info['dep_counts']['pip'] = dep_count
                    dep_info['details'].append(f"pip: {dep_count} requirements")
            except Exception:
                pass
        
        # Check pyproject.toml for Python (Poetry format)
        pyproject = project_path / 'pyproject.toml'
        if pyproject.exists():
            try:
                with open(pyproject, 'r') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # Look for Poetry dependencies section
                    in_poetry_deps = False
                    in_dev_deps = False
                    poetry_deps = 0
                    dev_deps = 0
                    
                    for line in lines:
                        line = line.strip()
                        
                        # Check for Poetry dependencies sections
                        if line == '[tool.poetry.dependencies]':
                            in_poetry_deps = True
                            in_dev_deps = False
                        elif line.startswith('[tool.poetry.group.') and 'dependencies]' in line:
                            in_dev_deps = True
                            in_poetry_deps = False
                        elif line.startswith('[') and line != '[tool.poetry.dependencies]':
                            in_poetry_deps = False
                            in_dev_deps = False
                        
                        # Count dependencies
                        elif in_poetry_deps and line and not line.startswith('#') and '=' in line:
                            if not line.startswith('python'):  # Skip python version requirement
                                poetry_deps += 1
                        elif in_dev_deps and line and not line.startswith('#') and '=' in line:
                            dev_deps += 1
                    
                    # Also check for standard dependencies section (non-Poetry)
                    if 'dependencies = [' in content and poetry_deps == 0:
                        # Count items in dependencies array
                        deps_start = content.find('dependencies = [')
                        if deps_start != -1:
                            deps_section = content[deps_start:content.find(']', deps_start)]
                            poetry_deps = deps_section.count('"') // 2  # Rough count
                    
                    if poetry_deps > 0 or dev_deps > 0:
                        dep_info['has_deps'] = True
                        dep_info['languages'].append('Python')
                        total_deps = poetry_deps + dev_deps
                        dep_info['dep_counts']['poetry'] = total_deps
                        if dev_deps > 0:
                            dep_info['details'].append(f"poetry: {poetry_deps} deps, {dev_deps} dev deps")
                        else:
                            dep_info['details'].append(f"poetry: {poetry_deps} deps")
            except Exception:
                pass
        
        # Check go.mod for Go
        go_mod = project_path / 'go.mod'
        if go_mod.exists():
            try:
                with open(go_mod, 'r') as f:
                    lines = f.readlines()
                    dep_count = len([line for line in lines if line.strip() and not line.strip().startswith('module') and not line.strip().startswith('go')])
                    dep_info['has_deps'] = True
                    dep_info['languages'].append('Go')
                    dep_info['dep_counts']['go'] = dep_count
                    dep_info['details'].append(f"go: {dep_count} modules")
            except Exception:
                pass
        
        return dep_info
    
    def _get_github_repo(self, project_path: Path) -> Optional[str]:
        """Extract GitHub repository name from git remote"""
        try:
            original_cwd = os.getcwd()
            os.chdir(project_path)
            
            # Get remote URL
            result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return None
                
            remote_url = result.stdout.strip()
            
            # Parse GitHub URLs (both HTTPS and SSH)
            if 'github.com' in remote_url:
                if remote_url.startswith('git@github.com:'):
                    # SSH format: git@github.com:user/repo.git
                    repo_part = remote_url.replace('git@github.com:', '').replace('.git', '')
                elif remote_url.startswith('https://github.com/'):
                    # HTTPS format: https://github.com/user/repo.git
                    repo_part = remote_url.replace('https://github.com/', '').replace('.git', '')
                else:
                    return None
                    
                # Validate format (should be user/repo)
                if '/' in repo_part and len(repo_part.split('/')) == 2:
                    return repo_part
                    
            return None
            
        except Exception:
            return None
        finally:
            try:
                os.chdir(original_cwd)
            except Exception:
                pass
    
    def _fetch_github_info(self, repo_name: str, token: Optional[str] = None) -> Dict:
        """Fetch GitHub repository information via API"""
        try:
            # Prepare API request
            api_url = f"https://api.github.com/repos/{repo_name}"
            
            headers = {
                'User-Agent': 'ProjectHealthScanner/1.0',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            if token:
                headers['Authorization'] = f'token {token}'
            
            # Fetch basic repo info
            req = urllib.request.Request(api_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    
                    # Extract relevant information
                    github_info = {
                        'stars': data.get('stargazers_count', 0),
                        'open_issues': data.get('open_issues_count', 0),
                        'last_activity': None,
                        'workflow_status': 'unknown'
                    }
                    
                    # Parse last activity
                    updated_at = data.get('updated_at')
                    if updated_at:
                        try:
                            github_info['last_activity'] = datetime.fromisoformat(
                                updated_at.replace('Z', '+00:00')
                            )
                        except Exception:
                            pass
                    
                    # Try to get PR count (open issues includes PRs, so we need to subtract)
                    try:
                        pr_api_url = f"https://api.github.com/repos/{repo_name}/pulls?state=open"
                        pr_req = urllib.request.Request(pr_api_url, headers=headers)
                        
                        with urllib.request.urlopen(pr_req, timeout=5) as pr_response:
                            if pr_response.status == 200:
                                pr_data = json.loads(pr_response.read().decode())
                                open_prs = len(pr_data)
                                github_info['open_prs'] = open_prs
                                github_info['open_issues'] = max(0, data.get('open_issues_count', 0) - open_prs)
                    except Exception:
                        # If we can't get PR count, just use total as issues
                        github_info['open_prs'] = 0
                        github_info['open_issues'] = data.get('open_issues_count', 0)
                    
                    return github_info
                    
        except Exception as e:
            # Silently fail for GitHub API issues
            pass
            
        return {
            'stars': 0,
            'open_issues': 0,
            'open_prs': 0,
            'last_activity': None,
            'workflow_status': 'unknown'
        }
    
    def _check_project_quality(self, project_path: Path) -> Dict:
        """Check various project quality indicators"""
        quality_info = {
            'has_readme': False,
            'readme_quality': 0,  # 0-5 scale
            'has_tests': False,
            'test_coverage': 0,   # 0-5 scale estimate
            'has_ci_cd': False,
            'ci_cd_type': 'none',
            'has_documentation': False,
            'code_quality_tools': 0,  # Count of quality tools
            'project_structure': 0,   # 0-5 scale
        }
        
        try:
            # Check for README
            readme_files = ['README.md', 'README.rst', 'README.txt', 'readme.md']
            for readme_file in readme_files:
                readme_path = project_path / readme_file
                if readme_path.exists():
                    quality_info['has_readme'] = True
                    try:
                        with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Simple quality assessment based on length and content
                            if len(content) > 2000:
                                quality_info['readme_quality'] = 5
                            elif len(content) > 1000:
                                quality_info['readme_quality'] = 4
                            elif len(content) > 500:
                                quality_info['readme_quality'] = 3
                            elif len(content) > 200:
                                quality_info['readme_quality'] = 2
                            else:
                                quality_info['readme_quality'] = 1
                    except Exception:
                        quality_info['readme_quality'] = 1
                    break
            
            # Check for tests
            test_patterns = [
                'test/', 'tests/', '__tests__/', 'spec/',
                '*_test.py', '*.test.js', '*_test.js', '*_spec.py', '*.spec.js',
                'test_*.py', 'test*.py'
            ]
            
            test_count = 0
            for pattern in test_patterns:
                if '/' in pattern:
                    # Directory patterns
                    if (project_path / pattern.rstrip('/')).exists():
                        test_count += 1
                else:
                    # File patterns
                    test_files = list(project_path.rglob(pattern))
                    if test_files:
                        test_count += len(test_files)
            
            if test_count > 0:
                quality_info['has_tests'] = True
                quality_info['test_coverage'] = min(5, max(1, test_count // 2))
            
            # Check for CI/CD
            ci_files = [
                '.github/workflows/',
                '.gitlab-ci.yml',
                '.travis.yml', 
                'azure-pipelines.yml',
                'Jenkinsfile',
                'circle.yml',
                '.circleci/'
            ]
            
            for ci_file in ci_files:
                ci_path = project_path / ci_file
                if ci_path.exists():
                    quality_info['has_ci_cd'] = True
                    if 'github' in ci_file:
                        quality_info['ci_cd_type'] = 'GitHub Actions'
                    elif 'gitlab' in ci_file:
                        quality_info['ci_cd_type'] = 'GitLab CI'
                    elif 'travis' in ci_file:
                        quality_info['ci_cd_type'] = 'Travis CI'
                    elif 'azure' in ci_file:
                        quality_info['ci_cd_type'] = 'Azure Pipelines'
                    else:
                        quality_info['ci_cd_type'] = 'Other CI'
                    break
            
            # Check for documentation
            doc_indicators = [
                'docs/', 'doc/', 'documentation/',
                'wiki/', 'sphinx/', 'mkdocs.yml',
                'docusaurus.config.js'
            ]
            
            for doc_indicator in doc_indicators:
                if (project_path / doc_indicator).exists():
                    quality_info['has_documentation'] = True
                    break
            
            # Check for code quality tools
            quality_files = [
                '.eslintrc', '.eslintrc.js', '.eslintrc.json',
                '.flake8', 'setup.cfg', '.pylintrc',
                '.prettierrc', '.prettierrc.js', '.prettierrc.json',
                '.pre-commit-config.yaml',
                'mypy.ini', 'pyproject.toml',  # May contain linting config
                '.editorconfig'
            ]
            
            quality_tools = 0
            for quality_file in quality_files:
                if (project_path / quality_file).exists():
                    quality_tools += 1
                    
            quality_info['code_quality_tools'] = quality_tools
            
            # Assess project structure (basic heuristic)
            structure_score = 0
            common_dirs = ['src/', 'lib/', 'app/', 'components/', 'utils/', 'config/']
            for common_dir in common_dirs:
                if (project_path / common_dir).exists():
                    structure_score += 1
            
            # Additional points for organized structure
            if (project_path / 'package.json').exists() or (project_path / 'pyproject.toml').exists():
                structure_score += 1
                
            quality_info['project_structure'] = min(5, structure_score)
            
        except Exception:
            # If there are any errors, return default values
            pass
            
        return quality_info
    
    def _calculate_health_score(self, git_info: Dict, dep_info: Dict, github_info: Dict = None, quality_info: Dict = None) -> float:
        """Calculate a health score from 0-10 based on multiple factors"""
        score = 10.0
        
        # Deduct points for uncommitted changes (more severe penalty)
        if git_info['uncommitted'] > 0:
            if git_info['uncommitted'] > 50:
                score -= 3.0  # Lots of uncommitted changes
            elif git_info['uncommitted'] > 10:
                score -= 2.0  # Many uncommitted changes  
            else:
                score -= min(1.0, git_info['uncommitted'] * 0.1)  # Few uncommitted changes
        
        # Deduct points for old commits (more nuanced)
        if git_info['last_commit']:
            days_old = (datetime.now(git_info['last_commit'].tzinfo) - git_info['last_commit']).days
            if days_old > 365:  # Very old (1+ years)
                score -= 4.0
            elif days_old > 180:  # Old (6+ months)
                score -= 2.5
            elif days_old > 60:   # Somewhat old (2+ months)
                score -= 1.5
            elif days_old > 14:   # Recent but not current (2+ weeks)
                score -= 0.5
        
        # Small deduction for unknown remote status
        if git_info['remote_status'] == 'unknown':
            score -= 0.5
        
        # Bonus points for having dependencies (indicates active project)
        if dep_info['has_deps']:
            score += 0.5
            
            # Small bonus for reasonable number of dependencies
            total_deps = sum(dep_info['dep_counts'].values())
            if 5 <= total_deps <= 50:  # Reasonable number of deps
                score += 0.3
            elif total_deps > 100:    # Too many dependencies
                score -= 0.5
        
        # Bonus for multiple language support
        if len(dep_info['languages']) > 1:
            score += 0.2
        
        # GitHub-based scoring
        if github_info:
            # Penalize for too many open issues
            open_issues = github_info.get('open_issues', 0)
            if open_issues > 50:
                score -= 1.5
            elif open_issues > 20:
                score -= 1.0
            elif open_issues > 10:
                score -= 0.5
            
            # Small bonus for having some open PRs (indicates active development)
            open_prs = github_info.get('open_prs', 0)
            if 1 <= open_prs <= 5:
                score += 0.3
            elif open_prs > 10:
                score -= 0.3  # Too many PRs might indicate bottleneck
            
            # Small bonus for popular projects
            stars = github_info.get('stars', 0)
            if stars > 1000:
                score += 0.5
            elif stars > 100:
                score += 0.3
            elif stars > 10:
                score += 0.1
            
            # Bonus for recent GitHub activity
            last_activity = github_info.get('last_activity')
            if last_activity and git_info.get('last_commit'):
                # Compare GitHub activity with last commit
                days_since_github = (datetime.now(last_activity.tzinfo) - last_activity).days
                if days_since_github <= 7:
                    score += 0.2  # Very recent activity
        
        # Quality-based scoring
        if quality_info:
            # Documentation bonuses
            if quality_info['has_readme']:
                score += 0.3 + (quality_info['readme_quality'] * 0.1)  # 0.4-0.8 bonus
            
            if quality_info['has_documentation']:
                score += 0.4
            
            # Testing bonuses
            if quality_info['has_tests']:
                score += 0.5 + (quality_info['test_coverage'] * 0.1)  # 0.6-1.0 bonus
            
            # CI/CD bonus
            if quality_info['has_ci_cd']:
                score += 0.6
            
            # Code quality tools bonus
            quality_tools_bonus = min(0.5, quality_info['code_quality_tools'] * 0.1)
            score += quality_tools_bonus
            
            # Project structure bonus
            structure_bonus = quality_info['project_structure'] * 0.1  # 0-0.5
            score += structure_bonus
        
        return max(0.0, min(10.0, score))

class DashboardServer:
    """Simple HTTP server to serve the dashboard"""
    
    def __init__(self, projects: List[ProjectHealth], port: int = 8042):
        self.projects = projects
        self.port = port
        self.httpd = None
    
    def generate_html(self) -> str:
        """Generate HTML dashboard"""
        projects_json = json.dumps([asdict(p) for p in self.projects], default=str, indent=2)
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Project Health Scanner</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
            margin: 0; padding: 20px; background: #f5f5f7; 
        }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .stats {{ display: flex; gap: 20px; justify-content: center; margin-bottom: 40px; }}
        .stat {{ background: white; padding: 20px; border-radius: 8px; text-align: center; min-width: 100px; }}
        .projects {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }}
        .project {{ 
            background: white; padding: 20px; border-radius: 8px; 
            border-left: 4px solid #007AFF; 
        }}
        .project.healthy {{ border-left-color: #28a745; }}
        .project.warning {{ border-left-color: #ffc107; }}
        .project.unhealthy {{ border-left-color: #dc3545; }}
        .health-score {{ font-size: 24px; font-weight: bold; }}
        .languages {{ margin: 10px 0; }}
        .language-tag {{ 
            display: inline-block; background: #007AFF; color: white; 
            padding: 2px 8px; border-radius: 4px; font-size: 12px; margin: 2px; 
        }}
        .git-info {{ font-size: 14px; color: #666; }}
        .chart-container {{ max-width: 600px; margin: 40px auto; }}
        .filters {{ 
            background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .filters h3 {{ margin-top: 0; margin-bottom: 15px; }}
        .filter-group {{ 
            display: inline-block; margin-right: 20px; margin-bottom: 10px; 
            vertical-align: top;
        }}
        .filter-group label {{ 
            display: block; margin-bottom: 5px; font-weight: 500; 
        }}
        .filter-group select, .filter-group input {{ 
            padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px;
            font-size: 14px; min-width: 150px;
        }}
        #clearFilters {{ 
            padding: 8px 16px; background: #007AFF; color: white; border: none; 
            border-radius: 4px; cursor: pointer; margin-left: 10px;
        }}
        #clearFilters:hover {{ background: #0056b3; }}
        .project.hidden {{ display: none !important; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 Project Health Dashboard</h1>
        <p>Monitoring {len(self.projects)} projects • Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="filters">
        <h3>🔍 Filter Projects</h3>
        <div class="filter-group">
            <label for="healthFilter">Health Status:</label>
            <select id="healthFilter">
                <option value="all">All Projects</option>
                <option value="healthy">Healthy (8-10)</option>
                <option value="warning">Warning (5-8)</option>
                <option value="unhealthy">Unhealthy (0-5)</option>
            </select>
        </div>
        
        <div class="filter-group">
            <label for="languageFilter">Language:</label>
            <select id="languageFilter">
                <option value="all">All Languages</option>
            </select>
        </div>
        
        <div class="filter-group">
            <label for="githubFilter">GitHub:</label>
            <select id="githubFilter">
                <option value="all">All Projects</option>
                <option value="github">Has GitHub</option>
                <option value="no-github">No GitHub</option>
            </select>
        </div>
        
        <div class="filter-group">
            <label for="starsFilter">GitHub Stars:</label>
            <select id="starsFilter">
                <option value="all">Any Stars</option>
                <option value="popular">Popular (>100)</option>
                <option value="very-popular">Very Popular (>1000)</option>
                <option value="some-stars">Has Stars (>0)</option>
                <option value="no-stars">No Stars</option>
            </select>
        </div>
        
        <div class="filter-group">
            <label for="searchFilter">Search:</label>
            <input type="text" id="searchFilter" placeholder="Search project names...">
        </div>
        
        <button id="clearFilters">Clear All Filters</button>
    </div>

    <div class="stats">
        <div class="stat">
            <h3>Total Projects</h3>
            <div class="health-score" id="totalCount">{len(self.projects)}</div>
        </div>
        <div class="stat">
            <h3>Healthy Projects</h3>
            <div class="health-score" style="color: #28a745" id="healthyCount">{len([p for p in self.projects if p.health_score >= 8])}</div>
        </div>
        <div class="stat">
            <h3>Need Attention</h3>
            <div class="health-score" style="color: #ffc107" id="warningCount">{len([p for p in self.projects if 5 <= p.health_score < 8])}</div>
        </div>
        <div class="stat">
            <h3>Unhealthy</h3>
            <div class="health-score" style="color: #dc3545" id="unhealthyCount">{len([p for p in self.projects if p.health_score < 5])}</div>
        </div>
    </div>
    
    <div class="chart-container">
        <canvas id="healthChart"></canvas>
    </div>
    
    <div class="projects" id="projects"></div>
    
    <script>
        const projects = {projects_json};
        
        // Render projects
        const projectsContainer = document.getElementById('projects');
        projects.forEach(project => {{
            const healthClass = project.health_score >= 8 ? 'healthy' : 
                               project.health_score >= 5 ? 'warning' : 'unhealthy';
            
            const languageTags = project.languages.map(lang => 
                `<span class="language-tag">${{lang}}</span>`
            ).join('');
            
            const lastCommit = project.last_commit ? 
                new Date(project.last_commit).toLocaleDateString() : 'Unknown';
            
            projectsContainer.innerHTML += `
                <div class="project ${{healthClass}}">
                    <h3>${{project.name}}</h3>
                    <div class="health-score" style="color: ${{
                        project.health_score >= 8 ? '#28a745' : 
                        project.health_score >= 5 ? '#ffc107' : '#dc3545'
                    }}">${{project.health_score.toFixed(1)}}/10</div>
                    <div class="languages">${{languageTags}}</div>
                    <div class="git-info">
                        📂 Branch: ${{project.branch}}<br>
                        📅 Last commit: ${{lastCommit}}<br>
                        📝 Uncommitted: ${{project.uncommitted_changes}}<br>
                        🔗 Remote: ${{project.remote_status}}
                    </div>
                </div>
            `;
        }});
        
        // Populate language filter options
        const allLanguages = [...new Set(projects.flatMap(p => p.languages))].sort();
        const languageFilter = document.getElementById('languageFilter');
        allLanguages.forEach(lang => {{
            const option = document.createElement('option');
            option.value = lang;
            option.textContent = lang;
            languageFilter.appendChild(option);
        }});
        
        // Get all project elements
        const projectElements = document.querySelectorAll('.project');
        
        // Filter functions
        function filterProjects() {{
            const healthFilter = document.getElementById('healthFilter').value;
            const languageFilter = document.getElementById('languageFilter').value;
            const githubFilter = document.getElementById('githubFilter').value;
            const starsFilter = document.getElementById('starsFilter').value;
            const searchFilter = document.getElementById('searchFilter').value.toLowerCase();
            
            let visibleProjects = [];
            
            projects.forEach((project, index) => {{
                const element = projectElements[index];
                let visible = true;
                
                // Health status filter
                if (healthFilter !== 'all') {{
                    if (healthFilter === 'healthy' && project.health_score < 8) visible = false;
                    if (healthFilter === 'warning' && (project.health_score < 5 || project.health_score >= 8)) visible = false;
                    if (healthFilter === 'unhealthy' && project.health_score >= 5) visible = false;
                }}
                
                // Language filter
                if (languageFilter !== 'all') {{
                    if (!project.languages.includes(languageFilter)) visible = false;
                }}
                
                // GitHub filter
                if (githubFilter !== 'all') {{
                    if (githubFilter === 'github' && !project.github_repo) visible = false;
                    if (githubFilter === 'no-github' && project.github_repo) visible = false;
                }}
                
                // Stars filter
                if (starsFilter !== 'all') {{
                    const stars = project.stars || 0;
                    if (starsFilter === 'popular' && stars <= 100) visible = false;
                    if (starsFilter === 'very-popular' && stars <= 1000) visible = false;
                    if (starsFilter === 'some-stars' && stars === 0) visible = false;
                    if (starsFilter === 'no-stars' && stars > 0) visible = false;
                }}
                
                // Search filter
                if (searchFilter && !project.name.toLowerCase().includes(searchFilter)) {{
                    visible = false;
                }}
                
                // Update visibility
                if (visible) {{
                    element.classList.remove('hidden');
                    visibleProjects.push(project);
                }} else {{
                    element.classList.add('hidden');
                }}
            }});
            
            // Update statistics
            updateStatistics(visibleProjects);
        }}
        
        function updateStatistics(visibleProjects) {{
            const total = visibleProjects.length;
            const healthy = visibleProjects.filter(p => p.health_score >= 8).length;
            const warning = visibleProjects.filter(p => p.health_score >= 5 && p.health_score < 8).length;
            const unhealthy = visibleProjects.filter(p => p.health_score < 5).length;
            
            document.getElementById('totalCount').textContent = total;
            document.getElementById('healthyCount').textContent = healthy;
            document.getElementById('warningCount').textContent = warning;
            document.getElementById('unhealthyCount').textContent = unhealthy;
        }}
        
        function clearFilters() {{
            document.getElementById('healthFilter').value = 'all';
            document.getElementById('languageFilter').value = 'all';
            document.getElementById('githubFilter').value = 'all';
            document.getElementById('starsFilter').value = 'all';
            document.getElementById('searchFilter').value = '';
            filterProjects();
        }}
        
        // Add event listeners
        document.getElementById('healthFilter').addEventListener('change', filterProjects);
        document.getElementById('languageFilter').addEventListener('change', filterProjects);
        document.getElementById('githubFilter').addEventListener('change', filterProjects);
        document.getElementById('starsFilter').addEventListener('change', filterProjects);
        document.getElementById('searchFilter').addEventListener('input', filterProjects);
        document.getElementById('clearFilters').addEventListener('click', clearFilters);
        
        // Create health distribution chart
        const ctx = document.getElementById('healthChart').getContext('2d');
        const healthScores = projects.map(p => p.health_score);
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: projects.map(p => p.name),
                datasets: [{{
                    label: 'Health Score',
                    data: healthScores,
                    backgroundColor: healthScores.map(score => 
                        score >= 8 ? '#28a745' : score >= 5 ? '#ffc107' : '#dc3545'
                    )
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Project Health Scores'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        max: 10
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
        return html
    
    def start_server(self):
        """Start the HTTP server"""
        class DashboardHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, dashboard=None, **kwargs):
                self.dashboard = dashboard
                super().__init__(*args, **kwargs)
            
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(self.dashboard.generate_html().encode())
        
        handler = lambda *args, **kwargs: DashboardHandler(*args, dashboard=self, **kwargs)
        
        try:
            with socketserver.TCPServer(("", self.port), handler) as httpd:
                self.httpd = httpd
                url = f"http://localhost:{self.port}"
                print(f"🚀 Dashboard running at {url}")
                
                # Open browser automatically
                webbrowser.open(url)
                
                httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Dashboard stopped")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Project Health Dashboard')
    parser.add_argument('--scan', default='~/Programming', 
                       help='Directory to scan for projects (default: ~/Programming)')
    parser.add_argument('--port', type=int, default=8042,
                       help='Port for web dashboard (default: 8042)')
    parser.add_argument('--no-browser', action='store_true',
                       help='Do not open browser automatically')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze projects, do not start web server')
    parser.add_argument('--output-html', type=str, metavar='FILENAME',
                       help='Generate static HTML report and save to file')
    parser.add_argument('--github-token', type=str, metavar='TOKEN',
                       help='GitHub personal access token for API access')
    
    args = parser.parse_args()
    
    print("🏥 Project Health Scanner")
    print("=" * 50)
    
    # Scan projects
    scanner = ProjectScanner(args.scan, args.github_token)
    projects = scanner.scan_projects()
    
    if not projects:
        print("❌ No projects found!")
        return 1
    
    print(f"\n📊 Analysis Complete!")
    print(f"   Total projects: {len(projects)}")
    print(f"   Healthy (8-10): {len([p for p in projects if p.health_score >= 8])}")
    print(f"   Warning (5-8):  {len([p for p in projects if 5 <= p.health_score < 8])}")
    print(f"   Unhealthy (0-5): {len([p for p in projects if p.health_score < 5])}")
    
    # Generate static HTML output if requested
    if args.output_html:
        dashboard = DashboardServer(projects, args.port)
        html_content = dashboard.generate_html()
        
        try:
            with open(args.output_html, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"📄 Static HTML report saved to: {args.output_html}")
            
            # Get absolute path for opening in browser
            html_path = os.path.abspath(args.output_html)
            file_url = f"file://{html_path}"
            
            print(f"🌐 Open in browser: {file_url}")
            
            # Optionally open in browser automatically
            if not args.no_browser:
                webbrowser.open(file_url)
                print("🚀 Opened report in browser")
            
            return 0
            
        except Exception as e:
            print(f"❌ Error saving HTML report: {e}")
            return 1
    
    # Print detailed results if analyze-only mode
    if args.analyze_only:
        print(f"\n📋 Project Details:")
        print(f"{'='*80}")
        for project in sorted(projects, key=lambda p: p.health_score, reverse=True):
            status_emoji = "✅" if project.health_score >= 8 else "⚠️" if project.health_score >= 5 else "❌"
            print(f"{status_emoji} {project.name} ({project.health_score:.1f}/10)")
            print(f"   📂 {project.path}")
            print(f"   🌿 Branch: {project.branch}")
            if project.last_commit:
                days_old = (datetime.now(project.last_commit.tzinfo) - project.last_commit).days
                print(f"   📅 Last commit: {project.last_commit.strftime('%Y-%m-%d')} ({days_old} days ago)")
            print(f"   📝 Uncommitted changes: {project.uncommitted_changes}")
            print(f"   💻 Languages: {', '.join(project.languages) if project.languages else 'None detected'}")
            print(f"   📦 Dependencies: {project.dependencies_status}")
            
            # GitHub information
            if project.github_repo:
                print(f"   🐙 GitHub: {project.github_repo}")
                if project.stars > 0:
                    print(f"   ⭐ Stars: {project.stars}")
                if project.open_issues > 0 or project.open_prs > 0:
                    print(f"   🐛 Issues: {project.open_issues} | 🔄 PRs: {project.open_prs}")
                if project.last_github_activity:
                    github_days = (datetime.now(project.last_github_activity.tzinfo) - project.last_github_activity).days
                    print(f"   📡 GitHub activity: {project.last_github_activity.strftime('%Y-%m-%d')} ({github_days} days ago)")
            
            print()
        return 0
    
    # Start dashboard server
    dashboard = DashboardServer(projects, args.port)
    if args.no_browser:
        print("Starting server without opening browser...")
    dashboard.start_server()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
