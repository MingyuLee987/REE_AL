"""Single entry point for the supported workflows."""
import importlib,sys

COMMANDS={'train':'train','predict':'predict','al':'active_learning','validate':'experiments','plot':'plotting'}

def main():
    if len(sys.argv)<2 or sys.argv[1] in ['-h','--help']:
        print('Usage: python -m corrosion_ml {train,predict,al,validate,plot} [options]')
        print('train      Train/evaluate the selected SVR')
        print('predict    Predict i_corr with the saved model')
        print('al         Simulate AL or recommend an experiment batch')
        print('validate   Validate your own measurements without retraining')
        print('plot       Plot the completed AL comparison')
        return
    command=sys.argv.pop(1)
    if command not in COMMANDS:raise SystemExit(f'Unknown command: {command}')
    importlib.import_module('corrosion_ml.'+COMMANDS[command]).main()

if __name__=='__main__':main()
