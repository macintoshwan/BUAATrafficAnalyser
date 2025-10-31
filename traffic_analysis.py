import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta
import numpy as np

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei']  # 微软雅黑或黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 读取CSV文件
df = pd.read_csv('output.csv', encoding='utf-8')

# 删除最后一行汇总数据
df = df[:-1]

# 数据清洗 - 转换日期格式
df['上线时间'] = pd.to_datetime(df['上线时间'])
df['下线时间'] = pd.to_datetime(df['下线时间'])

# 处理流量数据（字节转换为GB）
def parse_traffic(traffic_str):
    """将流量字符串转换为GB"""
    if pd.isna(traffic_str) or traffic_str == '0byte':
        return 0
    
    traffic_str = str(traffic_str)
    
    if 'G' in traffic_str:
        return float(traffic_str.replace('G', ''))
    elif 'M' in traffic_str:
        return float(traffic_str.replace('M', '')) / 1024
    elif 'K' in traffic_str:
        return float(traffic_str.replace('K', '')) / (1024 * 1024)
    elif 'byte' in traffic_str:
        return 0
    else:
        # 如果是纯数字（字节），转换为GB
        try:
            return float(traffic_str) / (1024 * 1024 * 1024)
        except:
            return 0

# 应用流量转换
df['流量_GB'] = df['总流量.1'].apply(parse_traffic)

# 过滤掉流量为0的记录
df = df[df['流量_GB'] > 0].copy()

# 按上线时间排序
df = df.sort_values('上线时间').reset_index(drop=True)

# 获取不同的IP地址并为每个IP分配颜色
unique_ips = df['IP地址'].unique()
colors = plt.cm.tab20(np.linspace(0, 1, len(unique_ips)))
ip_color_map = dict(zip(unique_ips, colors))

print(f"📊 开始绘制 {len(df)} 条记录...")

# 创建图表
fig, ax = plt.subplots(figsize=(20, 10))

# 为每条记录绘制矩形
cumulative_height = 0
daily_cumulative = {}  # 记录每天的累积高度

for idx, row in df.iterrows():
    start_date = row['上线时间']
    end_date = row['下线时间']
    traffic = row['流量_GB']
    ip = row['IP地址']
    
    # 计算时间跨度（以天为单位）
    duration = (end_date - start_date).total_seconds() / 86400  # 转换为天
    
    # 确保至少有一个最小宽度
    if duration < 0.01:  # 少于15分钟的会话至少显示为0.01天
        duration = 0.01
    
    # 获取该记录起始日期
    start_date_only = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 如果这一天还没有记录，初始化累积高度为0
    if start_date_only not in daily_cumulative:
        daily_cumulative[start_date_only] = 0
    
    # 在当前累积高度上绘制矩形
    rect = Rectangle((mdates.date2num(start_date), daily_cumulative[start_date_only]),
                     duration, traffic,
                     facecolor=ip_color_map[ip], 
                     edgecolor='white', 
                     linewidth=0.5,
                     alpha=0.7)
    ax.add_patch(rect)
    
    # 更新该日期的累积高度
    daily_cumulative[start_date_only] += traffic
    
    # 如果跨天，需要为后续的天也更新累积高度
    current_date = start_date_only + timedelta(days=1)
    end_date_only = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
    while current_date <= end_date_only:
        if current_date not in daily_cumulative:
            daily_cumulative[current_date] = 0
        daily_cumulative[current_date] += traffic
        current_date += timedelta(days=1)

# 计算每日总流量用于绘制顶部轮廓线
sorted_dates = sorted(daily_cumulative.keys())
daily_totals = [daily_cumulative[d] for d in sorted_dates]

# 绘制每日累积流量的轮廓线
ax.plot(sorted_dates, daily_totals, color='black', linewidth=2, 
        linestyle='-', alpha=0.8, label='每日累积流量', zorder=1000)

# 设置标题和标签
min_date = df['上线时间'].min()
max_date = df['下线时间'].max()
ax.set_title('校园网流量累积图 - 每条记录可视化\n从 {} 到 {}'.format(
    min_date.strftime('%Y-%m-%d'),
    max_date.strftime('%Y-%m-%d')
), fontsize=18, fontweight='bold', pad=20)

ax.set_xlabel('日期', fontsize=14, fontweight='bold')
ax.set_ylabel('流量 (GB)', fontsize=14, fontweight='bold')

# 设置x轴范围和格式
ax.set_xlim(mdates.date2num(min_date - timedelta(days=1)), 
            mdates.date2num(max_date + timedelta(days=1)))

# 格式化x轴日期
ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
days_span = (max_date - min_date).days
if days_span > 40:
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
else:
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
plt.xticks(rotation=45, ha='right')

# 添加网格
ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5, axis='y')
ax.set_axisbelow(True)

# 添加统计信息文本框
total_traffic = df['流量_GB'].sum()
days = (max_date.date() - min_date.date()).days + 1
avg_daily = total_traffic / days if days > 0 else 0
max_single = df['流量_GB'].max()
max_daily = max(daily_totals) if daily_totals else 0

stats_text = f'总流量: {total_traffic:.2f} GB\n时间跨度: {days} 天\n日均流量: {avg_daily:.2f} GB\n最大单次: {max_single:.2f} GB\n最高日累积: {max_daily:.2f} GB\nIP地址数: {len(unique_ips)}'
ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
        fontsize=11, verticalalignment='top', horizontalalignment='left',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

# 添加IP图例（只显示前10个最常用的IP）
ip_counts = df['IP地址'].value_counts().head(10)
legend_elements = [plt.Rectangle((0,0),1,1, facecolor=ip_color_map[ip], 
                                 edgecolor='white', alpha=0.7, label=f'{ip} ({count}次)')
                  for ip, count in ip_counts.items()]
ax.legend(handles=legend_elements, loc='upper right', fontsize=9, 
          title='主要IP地址（使用次数）', framealpha=0.9, ncol=1)

# 调整y轴范围，留出一些空间
ax.set_ylim(0, max(daily_totals) * 1.05 if daily_totals else 10)

# 调整布局
plt.tight_layout()

# 保存图表
plt.savefig('流量累积图.png', dpi=300, bbox_inches='tight')
print("✅ 流量累积图已生成：流量累积图.png")
plt.close()

# 输出统计信息
print("\n📊 统计摘要:")
print(f"总流量: {total_traffic:.2f} GB")
print(f"时间跨度: {days} 天")
print(f"日均流量: {avg_daily:.2f} GB")
print(f"最大单次流量: {max_single:.2f} GB")
print(f"最高日累积: {max_daily:.2f} GB")
print(f"记录条数: {len(df)} 条")
print(f"不同IP数: {len(unique_ips)}")
