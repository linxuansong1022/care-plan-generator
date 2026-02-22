import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
from .base import BaseIntakeAdapter, InternalOrder, InternalPatient, InternalProvider, AdapterError

class PharmaCorpAdapter(BaseIntakeAdapter):
    
    def parse(self, raw_data):
        # 1. 解包挑战：这回传进来的是二进制字符串或纯文本字符串
        try:
            # 万一接收到的是 django 传来的 bytes，我们要先解码成字符串
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode('utf-8')
                
            # 使用 ElementTree 这个 Python 自带的神器把 XML 变成“树”
            root = ET.fromstring(raw_data)
            return root
            
        except ParseError as e:
            raise AdapterError(f"PharmaCorp data must be valid XML. Error: {str(e)}")

    def transform(self, parsed_data) -> InternalOrder:
        # 2. 这里的 parsed_data 是一棵 XML 树的根节点 (root) 了！
        # 我们可以用 .findtext('路径') 来优雅地提取文字
        
        # 难点 A：获取所有的副诊断代码 <Code>，并变成列表
        # .findall 找出来的是一群 XML 节点对象，我们需要用 for 循环把每个节点的 .text 取出来
        nodes = parsed_data.findall('.//OtherDiagCodes/Code')
        additional_diags = [node.text for node in nodes if node.text]
        
        # 难点 B：把他们奇葩的美国生日格式 "11-20-1990" 变成标准的 "1990-11-20"
        raw_dob = parsed_data.findtext('.//Patient/DateOfBirth', '')
        standard_dob = ""
        if raw_dob and len(raw_dob) == 10:
            # 切片拼接：取后四位年，加上前两位月，加上中间两位日
            standard_dob = f"{raw_dob[6:10]}-{raw_dob[0:2]}-{raw_dob[3:5]}"
        
        # 难点 C：组装终极公文包
        return InternalOrder(
            patient=InternalPatient(
                first_name=parsed_data.findtext('.//Patient/GivenName', ''),
                last_name=parsed_data.findtext('.//Patient/SurName', ''),
                mrn=parsed_data.findtext('.//Patient/MedRecordNum', ''),
                dob=standard_dob  
            ),
            provider=InternalProvider(
                name=parsed_data.findtext('.//Prescriber/FullName', ''),
                npi=parsed_data.findtext('.//Prescriber/NationalProviderId', '')
            ),
            medication_name=parsed_data.findtext('.//ClinicalInfo/DrugName', ''),
            primary_diagnosis=parsed_data.findtext('.//ClinicalInfo/PrimaryDiagCode', ''),
            additional_diagnoses=additional_diags, 
            medication_history=[], # XML 里没这玩意，直接空列表
            patient_records="",
            confirm=False # 如果外网没传确认状态，默认算 False
        )
