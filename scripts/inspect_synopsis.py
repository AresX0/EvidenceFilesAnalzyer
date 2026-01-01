from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from case_agent.agent.agent import CaseAgent
import inspect
print('sig:', inspect.signature(CaseAgent.full_synopsis))
print('doc:', CaseAgent.full_synopsis.__doc__)
