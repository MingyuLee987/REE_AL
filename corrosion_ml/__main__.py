"""Single entry point for the supported workflows."""
import importlib,sys

COMMANDS={'predict':'predict'}

def main():
    if len(sys.argv)<2 or sys.argv[1] in ['-h','--help']:
        print('Usage: python -m corrosion_ml predict --data candidates.csv [--output results/predictions.csv]')
        print('predict    Predict i_corr with the saved model')
        return
    command=sys.argv.pop(1)
    if command not in COMMANDS:raise SystemExit(f'Unknown command: {command}')
    importlib.import_module('corrosion_ml.'+COMMANDS[command]).main()

if __name__=='__main__':main()
