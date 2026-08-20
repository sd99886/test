var myChart;
var timeIndex;
var categoryIndex;
var metricIndex;
var processedData;
var sortedTimes;
var chartData;
var updateFrequency = 2000;
var animationDuration = 1000;
var maxBars = 10;
var currentFrame = 0;
var timer;
var isPlaying = true;
var controlPanel;
var playPauseBtn;
var monthSelector;

function findIndexByValue(arr, value) {
    var i;
    for (i = 0; i < arr.length; i++) {
        if (arr[i].name === value) {
            return i;
        }
    }
    return -1;
}

function formatNumber(num) {
    if (num >= 10000) {
        return (num / 10000).toFixed(1) + 'W';
    }
    return Math.round(num).toLocaleString();
}

function renderChart() {
    if (!params.data || !params.data.schema || !params.data.data) {
        params.setInnerHTML('<div style="text-align:center;line-height:' + params.height + 'px;"><span>数据加载中或配置不完整...</span></div>');
        return;
    }

    myChart = params.getEchartsItem();

    if (!params.axes || params.axes.length < 3) {
        params.setInnerHTML('<div style="text-align:center;line-height:' + params.height + 'px;"><span>配置错误：请确保已拖入 [时间维度]、[二级品类维度] 和 [销售额度量] 3个字段。</span></div>');
        return;
    }

    timeIndex = 0;
    categoryIndex = 1;
    metricIndex = 2;

    processedData = {};
    var rows = params.data.data;
    var i;
    var row;
    var time;
    var category;
    var sales;
    
    for (i = 0; i < rows.length; i++) {
        row = rows[i];
        time = row[timeIndex];
        // 将时间格式统一为 yyyy-mm
        if (time && time.length >= 7) {
            time = time.substring(0, 7);
        }
        category = row[categoryIndex];
        sales = parseFloat(row[metricIndex]) || 0;

        if (!processedData[time]) {
            processedData[time] = {};
        }
        if (!processedData[time][category]) {
            processedData[time][category] = 0;
        }
        processedData[time][category] += sales;
    }

    sortedTimes = Object.keys(processedData).sort();
    chartData = [];

    var j;
    var k;
    var categories;
    var rankedCategories;
    var catName;
    var catKeys;
    
    for (j = 0; j < sortedTimes.length; j++) {
        time = sortedTimes[j];
        categories = processedData[time];
        rankedCategories = [];
        
        catKeys = Object.keys(categories);
        for (k = 0; k < catKeys.length; k++) {
            catName = catKeys[k];
            rankedCategories.push({ name: catName, value: categories[catName] });
        }
        
        rankedCategories.sort(function(a, b) { return b.value - a.value; });
        chartData.push({ time: time, data: rankedCategories });
    }

    if (chartData.length === 0) {
        params.setInnerHTML('<div style="text-align:center;line-height:' + params.height + 'px;"><span>没有足够的数据来生成动态图表。</span></div>');
        return;
    }

    createControlPanel();

    updateChart();
    startAnimation();

    myChart.on('click', function(echartsEvent) {
        params.onHSClickHandler([{
            data: echartsEvent.name === 'null' ? null : echartsEvent.name,
            path: categoryIndex
        }]);
    });

    params.bindUnmountHandler(function() {
        if (timer) {
            clearInterval(timer);
        }
    });
}

function createControlPanel() {
    var container = params.createElement('div');
    container.style.cssText = 'position:absolute;top:5px;left:5px;z-index:999;background:rgba(255,255,255,0.95);padding:6px 10px;border-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,0.15);display:flex;align-items:center;gap:8px;font-family:Arial,sans-serif;font-size:12px;';
    
    playPauseBtn = params.createElement('button');
    playPauseBtn.textContent = '暂停';
    playPauseBtn.style.cssText = 'padding:4px 10px;cursor:pointer;border:1px solid #ccc;border-radius:3px;background:#fff;font-size:12px;';
    playPauseBtn.onclick = function() {
        if (isPlaying) {
            pauseAnimation();
        } else {
            startAnimation();
        }
    };
    
    container.appendChild(playPauseBtn);

    var monthLabel = params.createElement('span');
    monthLabel.textContent = '月份：';
    monthLabel.style.cssText = 'color:#666;';
    container.appendChild(monthLabel);

    monthSelector = params.createElement('select');
    monthSelector.style.cssText = 'padding:4px 8px;cursor:pointer;border:1px solid #ccc;border-radius:3px;font-size:12px;min-width:100px;';
    
    var m;
    var option;
    for (m = 0; m < sortedTimes.length; m++) {
        option = params.createElement('option');
        option.value = m.toString();
        option.textContent = sortedTimes[m];
        monthSelector.appendChild(option);
    }
    
    monthSelector.onchange = function(event) {
        pauseAnimation();
        currentFrame = parseInt(event.target.value);
        updateChart();
    };
    
    container.appendChild(monthSelector);
    
    params.appendChild(container);
}

function updateChart() {
    if (chartData.length === 0) return;
    
    if (currentFrame >= chartData.length) {
        currentFrame = 0;
    }

    var frameData = chartData[currentFrame];
    var currentTime = frameData.time;
    var topCategories = frameData.data.slice(0, maxBars);

    // 使用衡石平台配置的颜色，如果没有则使用默认颜色
    var colors = params.chartConf && params.chartConf.color ? params.chartConf.color : 
                 ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#91cd77', '#f05b72', '#ef5b9c'];

    var yAxisData = [];
    var seriesData = [];
    var n;
    
    for (n = 0; n < topCategories.length; n++) {
        yAxisData.push(topCategories[n].name);
    }
    yAxisData.reverse();
    
    for (n = 0; n < topCategories.length; n++) {
        seriesData.push(topCategories[n].value);
    }
    seriesData.reverse();

    var option = {
        title: {
            text: '二级品类销售额动态排名',
            left: 'center',
            top: 50
        },
        xAxis: {
            type: 'value',
            max: 'dataMax',
            axisLabel: {
                formatter: function(n) {
                    return formatNumber(n);
                }
            }
        },
        yAxis: {
            type: 'category',
            data: yAxisData,
            inverse: true,
            animationDuration: 300,
            animationDurationUpdate: 300,
            max: maxBars - 1,
            axisLabel: {
                show: true,
                formatter: function(value) {
                    var index = findIndexByValue(topCategories, value);
                    return (index + 1) + '. ' + value;
                }
            }
        },
        series: [{
            realtimeSort: true,
            name: '销售额',
            type: 'bar',
            data: seriesData,
            label: {
                show: true,
                position: 'right',
                valueAnimation: true,
                formatter: function(param) {
                    return formatNumber(param.value);
                }
            },
            itemStyle: {
                borderRadius: [0, 4, 4, 0],
                color: function(param) {
                    return colors[param.dataIndex % colors.length];
                }
            }
        }],
        animationDuration: 0,
        animationDurationUpdate: animationDuration,
        animationEasing: 'linear',
        animationEasingUpdate: 'linear',
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'shadow'
            },
            formatter: function(params) {
                var dataIndex = params[0].dataIndex;
                var reversedIndex = topCategories.length - 1 - dataIndex;
                var category = topCategories[reversedIndex];
                return '<strong>' + category.name + '</strong><br/>' +
                       '销售额：' + formatNumber(category.value) + '<br/>' +
                       '排名：第' + (reversedIndex + 1) + '名';
            }
        },
        grid: {
            left: '3%',
            right: '15%',
            bottom: '3%',
            top: 80,
            containLabel: true
        }
    };

    myChart.setOption(option);
    
    if (monthSelector) {
        monthSelector.value = currentFrame.toString();
    }

    currentFrame++;
}

function startAnimation() {
    if (timer) {
        clearInterval(timer);
    }
    
    isPlaying = true;
    
    if (playPauseBtn) {
        playPauseBtn.textContent = '暂停';
    }
    
    timer = setInterval(updateChart, updateFrequency);
}

function pauseAnimation() {
    if (timer) {
        clearInterval(timer);
    }
    
    isPlaying = false;
    
    if (playPauseBtn) {
        playPauseBtn.textContent = '播放';
    }
}

renderChart();
