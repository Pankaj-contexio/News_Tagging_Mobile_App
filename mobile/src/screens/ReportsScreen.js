import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import api from '../api';
import { BarChart } from 'react-native-chart-kit';

export default function ReportsScreen() {
  const [report, setReport] = useState(null);

  useEffect(() => {
    const load = async () => {
      const response = await api.get('/reports');
      setReport(response.data);
    };
    load();
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Reports</Text>
      {report && (
        <BarChart
          data={report.chart}
          width={Dimensions.get('window').width - 32}
          height={220}
          chartConfig={{
            backgroundGradientFrom: '#fff',
            backgroundGradientTo: '#fff',
            color: (opacity = 1) => `rgba(0, 0, 255, ${opacity})`,
          }}
          style={styles.chart}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  },
  title: {
    fontSize: 20,
    marginBottom: 16,
    textAlign: 'center',
  },
  chart: {
    marginVertical: 8,
  },
});
