package com.cyberhirsch.nordwand;

import android.content.Context;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

/**
 * Streams the fused rotation-vector sensor to the web layer as a device->world (East, North, Up)
 * rotation matrix, row-major. Bypasses the WebView's DeviceOrientation API entirely.
 */
@CapacitorPlugin(name = "NordSensor")
public class NordSensorPlugin extends Plugin implements SensorEventListener {
    private SensorManager sm;
    private final float[] rot = new float[9];
    private long lastEmit = 0;
    private int accuracy = -1;

    @PluginMethod
    public void start(PluginCall call) {
        sm = (SensorManager) getContext().getSystemService(Context.SENSOR_SERVICE);
        Sensor s = sm.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
        String type = "ROTVEC";
        if (s == null) { s = sm.getDefaultSensor(Sensor.TYPE_GEOMAGNETIC_ROTATION_VECTOR); type = "GEOROT"; }
        if (s == null) { call.reject("No rotation sensor on this device"); return; }
        sm.unregisterListener(this);
        sm.registerListener(this, s, SensorManager.SENSOR_DELAY_GAME);
        JSObject r = new JSObject(); r.put("sensor", type); call.resolve(r);
    }

    @PluginMethod
    public void stop(PluginCall call) {
        if (sm != null) sm.unregisterListener(this);
        call.resolve();
    }

    @Override
    public void onSensorChanged(SensorEvent e) {
        long now = System.currentTimeMillis();
        if (now - lastEmit < 25) return; // ~40 Hz is plenty for the HUD
        lastEmit = now;
        SensorManager.getRotationMatrixFromVector(rot, e.values);
        JSArray m = new JSArray();
        for (float v : rot) m.put((double) v);
        JSObject d = new JSObject(); d.put("m", m); d.put("acc", accuracy);
        notifyListeners("rot", d);
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int acc) { accuracy = acc; }

    @Override
    protected void handleOnPause() { if (sm != null) sm.unregisterListener(this); }

    @Override
    protected void handleOnResume() {
        if (sm == null) return;
        Sensor s = sm.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
        if (s != null) sm.registerListener(this, s, SensorManager.SENSOR_DELAY_GAME);
    }
}
