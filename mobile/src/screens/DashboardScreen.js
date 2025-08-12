import React, { useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, Dimensions } from 'react-native';
import { useDispatch, useSelector } from 'react-redux';
import { fetchDashboard } from '../store/dashboardSlice';
import { LineChart } from 'react-native-chart-kit';

export default function DashboardScreen() {
  const dispatch = useDispatch();
  const { stats } = useSelector((state) => state.dashboard);

  useEffect(() => {
    dispatch(fetchDashboard());
  }, [dispatch]);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Dashboard</Text>
      {stats.chart && (
        <LineChart
          data={stats.chart}
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
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
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
