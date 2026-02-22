from .base import BaseIntakeAdapter, InternalOrder, InternalPatient, InternalProvider, AdapterError

class NordicHealthAdapter(BaseIntakeAdapter):
    """
    接收纯文本格式的订单
    PATIENT|Sven|Svensson|ND-8899|1985/12/31
    DOCTOR|Dr. Erik|7788990011
    ORDER|Ibuprofen|M10.9|M12.0;M15.3|CONFIRMED
    """
    
    def parse(self, raw_data):
        # 如果传过来的是 bytes，先解码成字符串
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode('utf-8')
            
        if not isinstance(raw_data, str):
            raise AdapterError("Nordic Health data must be a string.")
            
        # 按换行符切开，去掉多余的空行
        lines = [line.strip() for line in raw_data.split('\n') if line.strip()]
        return lines

    def transform(self, parsed_lines: list) -> InternalOrder:
        # 分门别类准备好几个空字典来装切碎的字段
        patient_data = {}
        provider_data = {}
        order_data = {'additional_diagnoses': []}
        
        # 逐行扫描，按竖线切开
        for line in parsed_lines:
            parts = line.split('|')
            if not parts:
                continue
                
            prefix = parts[0]
            
            if prefix == "PATIENT" and len(parts) >= 5:
                patient_data['first_name'] = parts[1]
                patient_data['last_name'] = parts[2]
                patient_data['mrn'] = parts[3]
                # 把他们的 1985/12/31 变成标准的 1985-12-31
                patient_data['dob'] = parts[4].replace('/', '-')
                
            elif prefix == "DOCTOR" and len(parts) >= 3:
                provider_data['name'] = parts[1]
                provider_data['npi'] = parts[2]
                
            elif prefix == "ORDER" and len(parts) >= 5:
                order_data['medication_name'] = parts[1]
                order_data['primary_diagnosis'] = parts[2]
                
                # 把副诊断 M12.0;M15.3 用分号切成列表
                raw_add_diags = parts[3]
                if raw_add_diags:
                    order_data['additional_diagnoses'] = [diag.strip() for diag in raw_add_diags.split(';')]
                
                # 判断是不是大写的 CONFIRMED
                order_data['confirm'] = (parts[4].strip().upper() == "CONFIRMED")

        # 组装神圣的公文包！
        return InternalOrder(
            patient=InternalPatient(
                first_name=patient_data.get('first_name', ''),
                last_name=patient_data.get('last_name', ''),
                mrn=patient_data.get('mrn', ''),
                dob=patient_data.get('dob', '')
            ),
            provider=InternalProvider(
                name=provider_data.get('name', ''),
                npi=provider_data.get('npi', '')
            ),
            medication_name=order_data.get('medication_name', ''),
            primary_diagnosis=order_data.get('primary_diagnosis', ''),
            additional_diagnoses=order_data.get('additional_diagnoses', []),
            medication_history=[], # 北欧医院格式里没有用药历史
            patient_records="",
            confirm=order_data.get('confirm', False)
        )
