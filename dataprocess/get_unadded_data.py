import json
import datetime


def extract_date_from_chunk_id(chunk_id):
    """从chunk_id中提取日期，格式为2025_MM_DD.txt"""
    date_str = chunk_id.replace('.txt', '')
    date_str = date_str.replace('_', '-')
    return datetime.datetime.strptime(date_str, '%Y-%m-%d')

def sort_log_data():
    with open('data/cleand_data/data_json_log.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    sorted_data = sorted(data, key=lambda x: extract_date_from_chunk_id(x['chunk_id']), reverse=True)
    
    with open('data/cleand_data/data_json_log.json', 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)
    
    print("数据已按日期从大到小排序完成！")
    print(f"总共处理了 {len(sorted_data)} 条记录")
    print("最新一条日志的日期：")
    date = extract_date_from_chunk_id(sorted_data[0]['chunk_id'])
    print(f"{sorted_data[0]['chunk_id']} - {date.strftime('%Y年%m月%d日')}")
    return date

def get_unadded_log_list():
    last_log_date = sort_log_data()
    today_date = datetime.datetime.today().date()  
    last_log_date = last_log_date.date()  
    
    # 从最后一天的下一天开始
    start_date = last_log_date + datetime.timedelta(days=1)
    # 生成从start_date到今天的日期列表（包含今天）
    unadded_log_list = []
    current_date = start_date
    while current_date <= today_date:  
        unadded_log_list.append(current_date.strftime("%Y_%m_%d.txt"))
        current_date += datetime.timedelta(days=1)
    
    return unadded_log_list

if __name__ == "__main__":
    unadded_log_list = get_unadded_log_list()
    print(unadded_log_list)