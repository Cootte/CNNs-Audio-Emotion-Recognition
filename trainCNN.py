import argparse,fileinput,os,sys,subprocess
import os
import random
import cPickle

#caffe_root = '../../caffe/' #PATH TO CAFFE ROOT
#sys.path.insert(0,caffe_root + 'python')
#import caffe
#caffe.set_device(0)
#caffe.set_mode_gpu()



#Parse the arguments
def ParseInputArguments():
   parser = argparse.ArgumentParser()

   # Parse input arguments
   parser.add_argument('net', help = 'path to network architecture')
   parser.add_argument('train', help = 'path to training data')
   parser.add_argument('test', help = 'path to test data')
   parser.add_argument('snapshot_prefix', help = 'prefix of the output network')
   parser.add_argument('max_iter', type = int, help = 'total number of iterations')
   parser.add_argument('--init', help = 'path to pre-trained model')
   parser.add_argument('--init_type', choices = ['fin','res'], help = "fin: for finetuning, res: for resuming training")
   parser.add_argument('--base_lr', default = 0.001, type = float, help = 'initial learning rate')
   parser.add_argument('--display', default = 20, type = int, help = 'display output every #display iterations')
   parser.add_argument('--test_interval', default = 500 , type = int, help = 'test every #test_interval iterations')
   parser.add_argument('--snapshot', default = 500, type = int, help = 'produce an output every #snapshot iterations')
   parser.add_argument('--type', default = 'SGD', choices = ['SGD','AdaDelta','AdaGrad','Adam','Nesterov','RMSProp'], help = 'back-propagation algorithm')
   parser.add_argument('--momentum',default = 0.9,  type = float, help = ' weight of the previous update')
   parser.add_argument('--lr_policy',default = 'step',choices=['step','fixed','exp','inv','multistep','poly','sigmoid'] ,help = 'learning rate decay policy')
   parser.add_argument('--test_iter', default = 75 , type = int, help = 'perform #test_iter iterations when testing')
   parser.add_argument('--stepsize', default = 700 , type = int, help = 'reduce learning rate every #stepsize iterations')
   parser.add_argument('--gamma',  default = 0.1, type = float, help = 'reduce learning rate to an order of #gamma')
   parser.add_argument('--weight_decay', default = 0.005, type = float, help = 'regularization term of the neural net')
   parser.add_argument('--solver_mode', default = 'CPU', choices = ['CPU','GPU'], help = 'where to run the program')
   parser.add_argument('--batch_size', default = 128, type = int, help = 'size of input batch')
   parser.add_argument('--input_size', default = 100, type = int, help = 'size of input image - images are always square')
   #parser.add_argument('--device_id', default = 0, type = int, choices=[0,1], help = '0:for CPU, 1: for GPU')
   args = parser.parse_args()
   solver = PrintSolverSetup(args)
   return args,solver

#Create the solver file .- Solver file works also as a descriptor for the experiment. -Extra information is written as comment
def PrintSolverSetup(args):   
   mode = 0
   solver = args.snapshot_prefix+"_solver.prototxt"
   print "Export experiment parameters to solver file:",solver
   fsetup = open(args.snapshot_prefix+"_solver.prototxt", 'w')
   for arg in vars(args):
     if arg is 'type':
        if str(getattr(args, arg)) == "AdaGrad":
		mode=1
     if mode==1 and arg is 'momentum':
	continue	
     if arg in ['init','train','test','init_type','batch_size','input_size']:
        fsetup.write('#')
     if (type(getattr(args, arg)) is str) and arg is not 'solver_mode':
	fsetup.write(arg +': "'+ str(getattr(args, arg))+'"\n')
	continue
     fsetup.write(arg +': '+ str(getattr(args, arg))+'\n')
   fsetup.write("test_state: { stage: 'test-on-test' }"+'\n')
   fsetup.write("test_initialization: false"+'\n')
   fsetup.write("random_seed: 1701")
   fsetup.close()
   return solver


#Change paths to training and  test data to the NETWORK.prototxt file
def ChangeNetworkDataRoots(train,test,ftrain,ftest,batch_size,input_size):
   
   for line in fileinput.input(args.net, inplace=True):
   	tmp = line.split(':')
   	initstring = tmp[0]
   	if tmp[0].strip() =='phase':
   		phase = tmp[1].strip()
   	if tmp[0].strip() == 'source':
   		if phase.upper() == 'TRAIN':
   			print initstring+": \""+ftrain+"\"\n",
   		else:
   			print initstring+": \""+ftest+"\"\n",
   		continue
   	if tmp[0].strip() =='root_folder':
   		if phase.upper() == 'TRAIN':
   			print initstring+": \""+train+'/\"\n',
   		else:
   			print initstring+": \""+test+'/\"\n',
   		continue
	if tmp[0].strip() =='batch_size':   		
   		print initstring+":"+ str(batch_size)+"\n",
   		continue	
	if tmp[0].strip() =='new_height' or tmp[0].strip() =='new_width' :   		
   		print initstring+":"+ str(input_size)+"\n",
   		continue   	
	print line,	
   	   

	# Create Source Files
def  CreateResourceFiles(snapshot_prefix,train,test):

    allLabels = list(set(os.listdir(train)+os.listdir(test)))
    allLabels = sorted(allLabels)
    StringTrain = []
    StringTest = []
    # Create Train Source File
    fnameTrain = snapshot_prefix + "_TrainSource.txt"
    train_file = open(fnameTrain, "w")
    for idx,label in enumerate(allLabels):
    	datadir = "/".join((train,label))
    	if os.path.exists(datadir):
           trainSamples = os.listdir(datadir)
           for sample in trainSamples:
             StringTrain.append('/'.join((label,sample))+' '+str(idx))
        	   

    # Create Test Source File
    fnameTest = snapshot_prefix + "_TestSource.txt"
    test_file = open(fnameTest, "w")
    for idx,label in enumerate(allLabels):
    	datadir = "/".join((test,label))
    	if os.path.exists(datadir):
           testSamples = os.listdir(datadir)
           for sample in testSamples:        	   
             StringTest.append('/'.join((label,sample))+' '+str(idx))

    random.shuffle(StringTrain)
    random.shuffle(StringTest)
    for s in StringTrain:      
      train_file.write(s+'\n')             
    for s in StringTest:      
      test_file.write(s+'\n')             

    train_file.close()      
    test_file.close()
    cPickle.dump(allLabels, open(snapshot_prefix + "_classNames", 'wb'))     
    return fnameTrain,fnameTest

# Modify execution file
def train(solver_prototxt_filename, init, init_type):
      for line in fileinput.input('train_net.sh', inplace=True):
              if '-solver' in line:
                 tmp = line.split('-solver')
                 if init==None:
                     print tmp[0]+" -solver "+ solver_prototxt_filename
                 elif init_type == 'fin':
                     print tmp[0]+" -solver "+ solver_prototxt_filename +" -weights " + init # .caffemodel file requiered for finetuning
                 elif init_type == 'res':
                     print tmp[0]+" -solver "+ solver_prototxt_filename +" -snapshot " + init # .solverstate file requiered for resuming training
                 else:
                     raise ValueError("No specific init_type defined for pre-trained network "+init)
              else:
                     print line,
      os.system("chmod +x train_net.sh")
      os.system('./train_net.sh')

if __name__ == "__main__":
    args,solver = ParseInputArguments()
    ftrain,ftest = CreateResourceFiles(args.snapshot_prefix,args.train,args.test)
    ChangeNetworkDataRoots(args.train,args.test,ftrain,ftest,args.batch_size,args.input_size)
    train(solver,args.init,args.init_type)
   
