import tables
import numpy as np
from math import ceil, floor
import matplotlib.pyplot as plt
from statistics import mean
import os
from tkinter import Tk, filedialog
import xlsxwriter
import glob

def between_two_hyphens(x):
    x1 = x[::-1]
    index = x1.find('_')
    val = x[-1*index:-4]
    return(int(val))

def main():
    print("Author: Carlo Pane, Last Update 13/03/20")
    #Load files from a directory
    while 1:
        key = input("|Press ENTER to run in single file mode. | |Press '0' & ENTER to run in entire folder mode. | | Press 'q' & ENTER to exit program||\n")
        single = True
        if key == '0':
            single = False
        elif key == 'q':
            print("Program Terminated as q has been pressed. Bye.")
            break

        root = Tk()
        root.withdraw()
        directory = filedialog.askdirectory()
        #directory = r'C:/Users/cpane/Documents/Taste of Research/Images'

        count = 1
        #add to excel
        # Workbook is created 
        print(directory)
        wb = xlsxwriter.Workbook(directory + '/data.xlsx')
        # add_sheet is used to create sheet. 
        bold = wb.add_format({'bold': True})
        sheet1 = wb.add_worksheet()
        sheet1.write(0, 0, 'filename',bold) 
        sheet1.write(0, 1, 'systolic',bold) 
        sheet1.write(0, 2, 'diastolic',bold) 
        sheet1.write(0, 3, 'RI',bold) 
        sheet1.write(0, 4, 'PI',bold) 
        sheet1.write(0, 5, 'S/D ratio',bold) 
        directory = directory + '/'
        files = sorted(os.listdir(directory), key=between_two_hyphens)
        for filename in files:
            if filename.endswith(".raw"):
                dataDict = processImage(os.path.join(directory, filename))
                sheet1.write(count, 0, filename) 
                sheet1.write(count, 1, dataDict['systolic'])
                sheet1.write(count, 2, dataDict['diastolic']) 
                sheet1.write(count, 3, dataDict['RI']) 
                sheet1.write(count, 4, dataDict['PI'])
                sheet1.write(count, 5, dataDict['SDratio']) 
                count = count + 1
                if single == True:
                    input("Press Enter for Next Image!")
            else:
                continue
        wb.close()
        print("Next Folder.............")
    input("Press any other key to close window")


def processImage(file):
    #Read in hdf5 table
    print("Current file processed: ", file)
    raw_file = tables.open_file(file, mode='r')
    #raw_file = tables.open_file('/Users/cpane/Documents/Taste of Research/Images/IMG_20180822_11_24.raw', mode='r')

    #Using hdf5 reader, the graph is located via this node path
    raw_file.__contains__("/MovieGroup2/AcqPWCW/RawData/")

    #Extract table data-----------------------------------------------------------------------------------
    node_raw_data = raw_file.get_node("/MovieGroup2/AcqPWCW/RawData/")

    wf_rawData = np.array(node_raw_data.RawDataUnit) #Matrix of 128 Samples per line, there are 937 lines
    #print(np.size(wf_rawData[0])) #Check to confirm size of row/no. of columns
    wf_samplePerLines = np.array(node_raw_data.SamplesPerLine)[0]

    #TimeStamps
    timeStamps = np.array(node_raw_data.TimeStamp)

    #Number of Lines
    numLines = np.size(np.array(node_raw_data.Lines))
    #print(numLines)

    #Reformat the Matrix
    node_ViewerPWCW = raw_file.get_node("/MovieGroup2/ViewerPWCW/")
    BasePoint_y = np.array(node_ViewerPWCW.BasePoint_y)[0]
    hrs_rect_top = np.array(node_ViewerPWCW.hrs_rect_top)[0]
    hrs_rect_bottom = np.array(node_ViewerPWCW.hrs_rect_bottom)[0]
    hrs_rect_left = np.array(node_ViewerPWCW.hrs_rect_left)[0]
    hrs_rect_right = np.array(node_ViewerPWCW.hrs_rect_right)[0]

    #Trace 
    traceLeft = np.array(node_ViewerPWCW.auto_trace_eval_region_left)[0]
    traceRight = np.array(node_ViewerPWCW.auto_trace_eval_region_right)[0]
    traceLeftFrac = (traceLeft-hrs_rect_left)/(hrs_rect_right - hrs_rect_left)
    traceRightFrac = (traceRight-hrs_rect_left)/(hrs_rect_right - hrs_rect_left)
    #Boundaries of the matrix columns
    traceMatrixLeft = ceil(traceLeftFrac * numLines)
    traceMatrixRight = ceil(traceRightFrac * numLines)

    #Get the top and bottom velocities of the viewer
    topV = np.array(node_ViewerPWCW.top_velocity)[0]
    bottomV = np.array(node_ViewerPWCW.bottom_velocity)[0]
    #print(topV, bottomV)

    #Roll the Matrix
    wf_rawData_boolean = wf_rawData > 0.025
    #print(np.shape(wf_rawData_boolean))
    #print(wf_rawData_boolean)

    #print(wf_rawData_roll_transpose_boolean)
    rowIndex = np.full((numLines), 0)


    #Just a little snippet to test the .index() function
    #.index() only returns the first index position
    '''
    testlist = [True,False,False,False]
    testlistR = testlist[::-1]
    indexL = testlistR.index(False)
    print(testlistR)
    print("IndexL",indexL)
    '''

    for i in range(numLines):
        try:
            wf_rawData_boolean_list = wf_rawData_boolean[i].tolist()
            wf_rawData_boolean_list_R = wf_rawData_boolean_list[::-1]
            rowIndex[i] = wf_rawData_boolean_list_R.index(False)
        except:
            continue
        
    #print(rowIndex)


    #Convert the rowIndex index value (0-128) to a value which is mapped to bottomV to topV
    #Works because the rawData matrix is not rolled
    rowIndexScaled = (np.array(rowIndex) * ((topV - bottomV)/ wf_samplePerLines))
    #print("I am a rowIndexScaled ", rowIndexScaled[0])
    #Have a variable filter value 0.025

    #Plotting the data----------------------------------------------------------------------------------------

    #Image View
    plt.figure(1)
    plt.clf()
    plt.subplot(211)
    plt.imshow(wf_rawData_boolean.T,  interpolation='nearest', aspect='auto')

    #plt.show()

    rowIndexScaledSmooth = [None] * numLines
    rowIndexScaledSmooth[0] = rowIndexScaled[0]

    for i in range(1,numLines):
        if abs(rowIndexScaled[i] - rowIndexScaledSmooth[i-1]) > 30:
            rowIndexScaledSmooth[i] = rowIndexScaledSmooth[i-1]
        else:
            rowIndexScaledSmooth[i] = rowIndexScaled[i]

    if not traceMatrixLeft:
        traceMatrixLeft = 1

    #Plot against time
    plt.subplot(212)
    plt.plot(timeStamps[0:traceMatrixLeft], rowIndexScaledSmooth[0:traceMatrixLeft],'b-',
    timeStamps[traceMatrixLeft-1:traceMatrixRight], rowIndexScaledSmooth[traceMatrixLeft-1:traceMatrixRight],'r-', 
    timeStamps[traceMatrixRight-1:], rowIndexScaledSmooth[traceMatrixRight-1:],'b-')


    firstMin = min(rowIndexScaledSmooth[traceMatrixLeft-1:ceil(traceMatrixRight - (traceMatrixRight-traceMatrixLeft)/2)])
    secondMin = min(rowIndexScaledSmooth[traceMatrixRight-60:traceMatrixRight])


    systolic = max(rowIndexScaledSmooth[traceMatrixLeft-1:traceMatrixRight])
    diastolic = secondMin
    RI = (systolic-diastolic)/systolic

    firstMinIndex = rowIndexScaledSmooth[traceMatrixLeft-1:ceil(traceMatrixRight - (traceMatrixRight-traceMatrixLeft)/2)].index(firstMin)
    secondMinIndex = rowIndexScaledSmooth[traceMatrixRight-60:traceMatrixRight].index(secondMin)
    firstMinIndex = traceMatrixLeft-1 + firstMinIndex
    secondMinIndex = traceMatrixRight-60 + secondMinIndex

    plt.plot(timeStamps[firstMinIndex],rowIndexScaledSmooth[firstMinIndex],'bx')
    plt.plot(timeStamps[secondMinIndex],rowIndexScaledSmooth[secondMinIndex],'bx')
    plt.show(block = False)
    #print(traceMatrixLeft, firstMinIndex, secondMinIndex, traceMatrixRight)

    PI = (systolic-diastolic)/(mean(rowIndexScaledSmooth[firstMinIndex:secondMinIndex]))

    #print(mean(rowIndexScaledSmooth[firstMinIndex:secondMinIndex]))
    SDratio = systolic/diastolic
    print(f"Systolic: {systolic}, Diastolic: {diastolic}")
    print(f"RI: {RI}")
    print(f"PI: {PI}")
    return {'systolic':systolic,'diastolic':diastolic,'RI':RI,'PI':PI, 'SDratio':SDratio}

if __name__ == "__main__":
    main()
