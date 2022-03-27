import requests,json,hashlib
import urllib.parse
from random import choices
import datetime,os,time
from configparser import ConfigParser
from rich.console import Console
from rich.table import Column, Table
from rich.progress import track
console = Console()
session = requests.session()
requests.packages.urllib3.disable_warnings()
users=[]
noticeId=[]
passed=[]
config={}
version="v.2.2.0"
def printUserInfo():
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("用户名", style="dim", width=12)
    table.add_column("登录状态")
    table.add_column("课程列表", justify="right")
    table.add_column("签到状态", justify="right")
    for user in users:
        if(user['stats']==0):
            table.add_row(user['account'],"[red]未登录[/red]","[red]无法加载[/red]","[red]无法开启[/red]")
        else:
            table.add_row(user['account'],"[green]登录成功[/green]","已经加载%s门"%(len(user['courseList'])),"[red]未开启[/red]")
    console.print(table)

def printConfig():
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("循环时间")
    table.add_column("检测前N条任务")
    table.add_column("server酱通知", justify="right")
    table.add_column("Bark通知", justify="right")
    n1="未开启"
    n2="未开启"
    if(config['serverKey']!=""):
        n1="开启"
    if(config['barkKey']!=""):
        n2="开启"
    table.add_row(str(config['sleep'])+"秒",str(config['count']),n1,n2)
    console.print(table)

def md5(data):
    res=hashlib.md5(data.encode(encoding='UTF-8')).hexdigest()
    return res
#{"account":"","password":""}
def updateUserInfo(account,key,value):
    global users
    for i in users:
        if(i['account']==account):
            i[key]=value
            return 1
    return 0

def getUserInfo(account,key):
    for i in users:
        if(i['account']==account):
            return i[key],i['stats']
    return -1,0

def login(uname,code):
    url="https://passport2-api.chaoxing.com/v11/loginregister?code="+code+"&cx_xxt_passport=json&uname="+uname+"&loginType=1&roleSelect=true"
    res=session.get(url)
    data = requests.utils.dict_from_cookiejar(session.cookies)
    mycookie=""
    for key in data:
        mycookie+=key+"="+data[key]+";"
    d=json.loads(res.text)
    if(d['mes']=="验证通过"):
        url="https://sso.chaoxing.com/apis/login/userLogin4Uname.do"
        res=session.get(url)
        a=json.loads(res.text)
        if(a['result']==1):
            myuid=str(a['msg']['puid'])
            #updateUserInfo(uname,"cookie",mycookie)
            #updateUserInfo(uname,"uid",myuid)
            #updateUserInfo(uname,"stats",1)
            return {"cookie":mycookie,"uid":myuid}
        else:
            console.log(uname+"获取UID失败",style="bold red")
    return 0

def checkCookie(account):
    url='https://sso.chaoxing.com/apis/login/userLogin4Uname.do'
    headers=getheaders(account)
    if(headers==0):
        return 0
    res=requests.get(url,headers=headers)
    data=json.loads(res.text)
    if(data['result']==0):
        return 1
    else:
        return 0

#获取同意请求头 包含Cookie
def getheaders(account):
    mycookie,stats=getUserInfo(account,"cookie")
    if(mycookie==-1 or stats==0):
        return 0
    headers={"Accept-Encoding": "gzip",
    "Accept-Language": "zh-Hans-CN;q=1, zh-Hant-CN;q=0.9",
    "Cookie": mycookie,
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 com.ssreader.ChaoXingStudy/ChaoXingStudy_3_4.8_ios_phone_202012052220_56 (@Kalimdor)_12787186548451577248",}
    return headers

def checkCookieTmp(cookie):
    url='https://sso.chaoxing.com/apis/login/userLogin4Uname.do'
    headers={"Accept-Encoding": "gzip",
    "Accept-Language": "zh-Hans-CN;q=1, zh-Hant-CN;q=0.9",
    "Cookie": cookie,
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 com.ssreader.ChaoXingStudy/ChaoXingStudy_3_4.8_ios_phone_202012052220_56 (@Kalimdor)_12787186548451577248",}
    res=requests.get(url,headers=headers)
    data=json.loads(res.text)
    if(data['result']==1):
        return 1
    else:
        return 0

#获取课程列表
def getcourse(account):
    url="http://mooc1-api.chaoxing.com/mycourse/backclazzdata?view=json&rss=1"
    headers=getheaders(account)
    if(headers==0):
        return 0
    res=requests.get(url,headers=headers)
    if('请重新登录' in res.text):
        return 0
    else:
        d=json.loads(res.text)
        courselist=d['channelList']
        return courselist

def initCourse():
    for user in users:
        if(user['stats']==1):
            data=getcourse(user['account'])
            if(data==0):
                console.log('用户'+user['account']+"读取课程列表失败,请检查账号登录状态,可以尝试重新运行程序",style="bold red")
                updateUserInfo(user['account'],"courseList",[])
            else:
                updateUserInfo(user['account'],"courseList",data)
        else:
            updateUserInfo(user['account'],"courseList",[])

def initConfig():
    global users,config
    CONFIGFILE = "config.ini"
    isExists=os.path.exists("data")
    if not isExists:
        os.makedirs("data")
    try:
        pconfig = ConfigParser()
        pconfig.read(CONFIGFILE,encoding='gbk')
        usercount=pconfig['全局配置'].getint('usercount')
        config['sleep']=pconfig['全局配置'].getint('sleep')
        if(config['sleep']<40):
            console.log("循环间隔设置过小,会造成严重后果,如账号被冻结访问,无法进行操作等,建议修改,请按任意键确认后继续",style="bold red")
            input()
        config['count']=pconfig['全局配置'].getint('count')
        config['serverKey']=pconfig['通知'].get('serverKey')
        config['barkKey']=pconfig['通知'].get('barkKey')
        for i in range(1,usercount+1):
            if '用户'+str(i) in pconfig.sections():
                tmpinfo={"account":"","password":"","stats":0}
                account=pconfig['用户'+str(i)].get('account')
                password=pconfig['用户'+str(i)].get('password')
                tmpinfo['account']=account
                tmpinfo['password']=password
                tmpinfo['name']=pconfig['用户'+str(i)].get('name')
                tmpinfo['oid']=pconfig['用户'+str(i)].get('oid')
                tmpinfo['address']=pconfig['用户'+str(i)].get('address')
                tmpinfo['lat']=pconfig['用户'+str(i)].get('lat')
                tmpinfo['long']=pconfig['用户'+str(i)].get('long')
                if(os.path.isfile('data/'+account+'.json')):
                    with open('data/'+account+'.json','r',encoding = "utf-8") as f:
                        tmp=f.read()
                        tmpdata=json.loads(tmp)
                        tmpinfo['cookie']=tmpdata['cookie']
                        tmpinfo['uid']=tmpdata['uid']
                        res=checkCookieTmp(tmpdata['cookie'])
                        if(res==1):
                            tmpinfo['stats']=1
                            console.log('用户'+str(i)+"身份信息依然有效,登录成功",style="bold green")
                        else:
                            tmpinfo['stats']=0
                            console.log('用户'+str(i)+"身份信息过期,需要重新登录",style="bold yellow")
                if(tmpinfo['stats']==0):
                    loginRes=login(account,password)
                    if(loginRes==0):
                        tmpinfo['stats']=0
                        console.log('用户'+str(i)+"登录失败,请检查账号密码是否正确",style="bold red")
                    else:
                        with open('data/'+account+'.json',"w",encoding = "utf-8") as f:
                            f.write(json.dumps(loginRes))
                        tmpinfo['cookie']=loginRes['cookie']
                        tmpinfo['uid']=loginRes['uid']
                        tmpinfo['stats']=1
                        console.log('用户'+str(i)+"登录成功 UID:"+loginRes['uid'],style="bold green")
                users.append(tmpinfo)
                #console.log('用户'+str(i)+"读取成功",style="bold green")
            else:
                console.log('用户'+str(i)+"不存在,请保持「全局配置」中的usercount与实际用户配置数量一致",style="bold yellow")
        #console.log("读取配置文件成功",style="bold green")
    except Exception as e:
        console.log("配置文件config.ini读取出错,请尝试还原该文件后重新修改",style="bold red")
        console.log("具体报错如下:\n"+str(e),style="bold red")

def showInfo():
    console.print("Hello, 欢迎使用炒饭学习通自动签到[bold magenta]"+version+"[/bold magenta]!")
    console.print("[*]本程序由炒饭进行开发,首发于公众号[bold green]给我一碗炒饭[/bold green]")
    console.print("[*]本程序开源地址为:[bold gray]https://github.com/w964522982/xxtSign[/bold gray]")
    console.print("[*]使用前请仔细阅读用户协议:[bold gray]https://github.com/w964522982/xxtSign/blob/main/Useragreement.txt[/bold gray] 使用即默认同意该协议")
    console.print("[*][bold red]本程序仅作为交流学习使用,请问用于非法用途,由用户造成的一切后果均与作者无关[/bold red]")
    console.print("[*]关注公众号[bold green]给我一碗炒饭[/bold green]获取更多新鲜好玩的知识,如遇到程序无法使用请在公众号或者github更新")
    console.print("[*]支持 普通|拍照|手势|位置|签到码 的自动签到,二维码需到小程序[bold green]「炒饭云签」[/bold green]进行手动签到")
    console.print("[*]拍照签到的图片以及位置签到的定位可在小程序[bold green]「炒饭云签」[/bold green]的个人设置中获取,如有能力可自行设置")
    console.print("---------------------------------------")

def ifopenAddress(aid):
    url="https://mobilelearn.chaoxing.com/newsign/signDetail?activePrimaryId="+aid+"&type=1"
    res=requests.get(url)
    d=json.loads(res.text)
    t=json.loads(d['content'])
    if(t['ifopenAddress']==1):
        return t
    else:
        return 0

def getTaskType(aid):
    url="https://mobilelearn.chaoxing.com/newsign/signDetail?activePrimaryId="+aid+"&type=1"
    res=requests.get(url)
    d=json.loads(res.text)
    if(d['otherId']==0):
        if(d['ifPhoto']==1):
            return 1
        else:
            return 2
    elif(d['otherId']==2):
        return 3
    elif(d['otherId']==3):
        return 6
    elif(d['otherId']==4):
        return 5
    elif(d['otherId']==5):
        return 7
    else:
        return 0

def notice(aid,account,msg):
    global noticeId
    if(md5(aid+account) in noticeId):
        return 0
    if(config['serverKey']!=""):
        url="https://sctapi.ftqq.com/"+config['serverKey']+".send?title=炒饭自动签到&desp="+msg
        requests.get(url)
    if(config['barkKey']!=""):
        url="https://api.day.app/"+config['barkKey']+"/炒饭自动签到/"+msg
        requests.get(url)
    noticeId.append(md5(aid+account))

def sign(aid,user,atype,coursename):
    global passed
    name=urllib.parse.quote(user['name'])
    uid=user['uid']
    oid=user['oid']
    address=user['address']
    lat=user['lat']
    long=user['long']
    if(md5(aid+user['account']) in passed):
        return 0
    if(atype==1):
        url="https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId="+aid+"&uid="+uid+"&clientip=&useragent=&latitude=-1&longitude=-1&appType=15&fid=0&objectId="+oid+"&name="+name
    elif(atype==2):
        url="https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId="+aid+"&uid="+uid+"&clientip=&latitude=-1&longitude=-1&appType=15&fid=0&name="+name
    elif(atype==6):
        url="https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId="+aid+"&uid="+uid+"&clientip=&useragent=&latitude=-1&longitude=-1&appType=15&fid=0&objectId=&name="+name
    elif(atype==5):
        info=ifopenAddress(aid)
        if(info==0):
            url="https://mobilelearn.chaoxing.com/pptSign/stuSignajax?name="+name+"&address="+address+"&activeId="+aid+"&uid="+uid+"&clientip=&latitude="+lat+"&longitude="+long+"&fid=0&appType=15&ifTiJiao=1"
        else:
            url="https://mobilelearn.chaoxing.com/pptSign/stuSignajax?name="+name+"&address="+info['locationText']+"&activeId="+aid+"&uid="+uid+"&clientip=&latitude="+info['locationLatitude']+"&longitude="+info['locationLongitude']+"&fid=0&appType=15&ifTiJiao=1"
    elif(atype==7):
        url="https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId="+aid+"&uid="+uid+"&clientip=&latitude=-1&longitude=-1&appType=15&fid=0&name="+name
    headers=getheaders(user['account'])
    if(headers==0):
        return 0
    res=requests.get(url,headers=headers)
    if(res.text=="success"):
        passed.append(md5(aid+user['account']))
        console.log("[+]"+aid+"签到成功",style="bold green")
        notice(aid,user['account'],"课程[%s]签到成功"%(coursename)+"--来自炒饭自动签到")
        return 1
    else:
        passed.append(md5(aid+user['account']))
        console.log("[x]签到失败,可能是已经签到过,或者账号登录失效,请在app中自行查看",style="bold yellow")
        return 0

def gettask(courseId,classId,uid,cpi,account,user,coursename):
    try:
        url="https://mobilelearn.chaoxing.com/ppt/activeAPI/taskactivelist?courseId="+courseId+"&classId="+classId+"&uid="+uid+"&cpi="+cpi
        headers=getheaders(account)
        if(headers==0):
            return 0
        res=requests.get(url,headers=headers)
        d=json.loads(res.text)
        if(d['result']==1):
            activeList=d['activeList']
            count=0
            n=0
            if(len(activeList)<config['count']):
                count=len(activeList)
            else:
                count=config['count']
            for active in activeList:
                if(n>count):
                    return 1
                status=active['status']
                aid=str(active['id'])
                if(status!=1):
                    n+=1
                    continue
                atype=getTaskType(aid)
                if(atype==0):
                    console.log("未知的签到类型,请及时查看更新",style="bold red")
                elif(atype==3):
                    notice(aid,account,account+"检测到二维码签到,无法自动签到,请使用小程序「炒饭云签」进行手动签到,更多内容请关注公众号「给我一碗炒饭」")
                    console.log("[-]二维码任务无法自动签到,请使用公众号[bold green]给我一碗炒饭[/bold green]的小程序[bold green]炒饭云签[/bold green]进行手动签到",style="bold yellow")
                elif(atype==1):
                    sign(aid,user,atype,coursename)
                    console.log("[-]"+account+"用户监测到拍照签到,此处使用的图片可在小程序[bold green]炒饭云签[/bold green]中进行获取objectId",style="bold yellow")
                elif(atype==2):
                    sign(aid,user,atype,coursename)
                    console.log("[-]"+account+"用户监测到普通签到",style="bold yellow")
                elif(atype==5):
                    sign(aid,user,atype,coursename)
                    console.log("[-]"+account+"用户监测到定位签到",style="bold yellow")
                elif(atype==6):
                    sign(aid,user,atype,coursename)
                    console.log("[-]"+account+"用户监测到手势签到",style="bold yellow")
                elif(atype==7):
                    sign(aid,user,atype,coursename)
                    console.log("[-]"+account+"用户监测到签到码签到",style="bold yellow")
                n+=1
    except Exception as e:
        print(e)

def check():
    for user in track(users,description="任务执行中..."):
        if(user['stats']==1):
            for course in user['courseList']:
                if('roletype' in course['content']):
                    roletype=course['content']['roletype']
                else:
                    continue
                if(roletype!=3):
                    continue
                classId=str(course['content']['id'])
                courseId=str(course['content']['course']['data'][0]['id'])
                cpi=str(course['content']['cpi'])
                coursename=course['content']['course']['data'][0]['name']
                gettask(courseId,classId,user['uid'],cpi,user['account'],user,coursename)
    console.log("此次任务执行完毕,程序正常运行中",style="bold green")

if __name__=="__main__":
    showInfo()
    initConfig()
    initCourse()
    printUserInfo()
    console.print("---------------------------------------")
    printConfig()
    input("请确认配置正确无误后,按任意键即可开始")
    while True:
        check()
        time.sleep(config['sleep'])