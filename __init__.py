import json
import xml.etree.ElementTree as ET 
import string
from datetime import datetime, timedelta
import sys
import traceback
import requests, base64
from models.common import Global
from models.output import Output


def createUrl(config: Global, url):
    return config.url.server + url


#Create login token
def createToken(config: Global):
    userPwd = config.username + ":" + config.password
    base64Auth = (base64.b64encode(userPwd.encode("UTF-8"))).decode("UTF-8")
    requestHeader = { "Authorization": "Basic %s" %base64Auth}
    response = requests.request("GET", createUrl(config, config.url.login), headers=requestHeader, verify=False)
    return response.headers[config.headertokenkey]
#end


#Load all available namespaces
def loadNamespaces(config: Global):
    headers = {
                config.headertokenkey: config.token
              }
    response = requests.request("GET", createUrl(config, config.url.namespaces), headers=headers, verify=False)
    result = response.text.encode(config.requestencoding)
    tree = ET.ElementTree(ET.fromstring(result))
    return list(tree.iter(tag ='id'))#id represents namespace
#end


#load all config values
def loadConfig():
    config = Global()
    with open('config.json') as json_file:
        data = json.load(json_file)
        config.customerfilepath = data['customerfilepath']
        config.logfile = data['logfile']
        config.errorfile = data['errorfile']
        config.fileformat = data['fileformat']
        config.startTime = data['starttime']
        config.endTime = data['endtime']
        config.daysdata = data['daysdata']
        config.requestencoding = data['requestencoding']
        config.url.server = data['url']['server']
        config.url.login = data['url']['login']
        config.url.namespaces = data['url']['namespaces']
        config.url.billing = data['url']['billing']
        config.username = data['username']
        config.password = data['password']
        config.headertokenkey = data['headertokenkey']
    return config


#function to write content to file 
def writeToFile(filePathName, content, accessRights):
    file = open(filePathName, accessRights)
    file.write(content)
    file.close()
#end


def header(config):
    return  {
                config.headertokenkey: config.token
            }



def process():

    try:

        #find today day, month and year
        day = datetime.now().strftime('%d')
        month = datetime.now().strftime('%B')
        year = datetime.now().strftime('%Y')
        #end


        #loading configuration from config.json
        config = loadConfig()
        #end
        
        #create token
        config.token = createToken(config)
        #end

        #loadnamespaces/clients
        namespaces = loadNamespaces(config)
        billingUrlPrefix = createUrl(config, config.url.billing)
        #iterate through each namespace and write logs in respective files
        for child_elem in namespaces:
            startPeriod = (datetime.now() - timedelta(days = config.daysdata)).strftime("%Y-%m-%dT") + config.startTime
            endPeriod = datetime.now().strftime("%Y-%m-%dT" + config.endTime)

            billingUrl = billingUrlPrefix + child_elem.text + "/sample?start_time="+ startPeriod +"&end_time=" + endPeriod + "&include_bucket_detail=false"
            response = requests.request("GET", billingUrl, headers = header(config), verify=False)
            result = response.text.encode(config.requestencoding)

            
            #Loading XML result and find required properties
            output = Output()
            tree = ET.ElementTree(ET.fromstring(result))
            root = tree.getroot()
            output.namespace = root.find('namespace').text
            output.totalsize = root.find('total_objects').text
            output.ingress = root.find('ingress').text
            output.egress = root.find('egress').text
            #end

            #writing the output to current day txt file
            customerDailyFileContent = "\n Total Size: " + output.totalsize + \
                                    "\n Ingress: " + output.ingress + \
                                    "\n Egress: " + output.egress

            writeToFile(config.customerfilepath + output.namespace + "_" + (day + "-" + month + "-" + year) + config.fileformat, customerDailyFileContent, "a+")
            #end

            #writing the output for to current month txt file
            #it will contain all outputs for current month
            customerMonthlyFileContent = "\n Date: " + day + "/" + month + "/" + year + \
                                        "\n Total Size: " + output.totalsize + \
                                        "\n Ingress: " + output.ingress + \
                                        "\n Egress: " + output.egress + \
                                        "\n-----------------------------------------------------------------------------------------------------------------------"
            writeToFile(config.customerfilepath + output.namespace + "_" + (month + "-" + year) + config.fileformat, customerMonthlyFileContent, "a+")
            #end

            #writing the output for to current month txt file
            #it will contain all outputs for current month
            logFileContent = "\n  Successfully executed at: " + datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + \
                            "\n-----------------------------------------------------------------------------------------------------------------------"
            writeToFile(config.logfile, logFileContent, "a+")
            #end

    #error handling
    except:
            #detail of error with datetime is logged in error file.
            t, v, tb = sys.exc_info()
            errorContent = "\n  Failed at: " + datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + \
                        "\n Error details: "

            for line in traceback.format_exception(t,v,tb): 
                errorContent = errorContent + line + '\n'
            
            errorContent = errorContent + "\n-----------------------------------------------------------------------------------------------------------------------"
            writeToFile(config.errorfile, errorContent, "a+")




def main():
    process()



if __name__ == "__main__":
    main()



