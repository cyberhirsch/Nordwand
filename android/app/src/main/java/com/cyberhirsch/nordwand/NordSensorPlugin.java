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
 * Two orientation streams, each as a device->world rotation matrix (row-major 3x3):
 *  "game" - GAME_ROTATION_VECTOR (gyro + accel, no magnetometer): smooth, immune to magnetic
 *           disturbance, arbitrary yaw origin. Drives the HUD.
 *  "rot"  - ROTATION_VECTOR (adds magnetometer): absolute north. Used only for the first guess
 *           and as a slow backup when no skyline/sun fix is available.
 */
@CapacitorPlugin(name = "NordSensor")
public class NordSensorPlugin extends Plugin implements SensorEventListener {
    private SensorManager sm;
    private Sensor game, rot;
    private final float[] m = new float[9];
    private long lastGame = 0, lastRot = 0;

    @PluginMethod
    public void start(PluginCall call) {
        sm = (SensorManager) getContext().getSystemService(Context.SENSOR_SERVICE);
        game = sm.getDefaultSensor(Sensor.TYPE_GAME_ROTATION_VECTOR);
        rot = sm.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR);
        if (game == null && rot == null) { call.reject("No rotation sensors on this device"); return; }
        register();
        JSObject r = new JSObject(); r.put("game", game != null); r.put("compass", rot != null); call.resolve(r);
    }

    @PluginMethod
    public void stop(PluginCall call) { if (sm != null) sm.unregisterListener(this); call.resolve(); }

    private void register() {
        sm.unregisterListener(this);
        if (game != null) sm.registerListener(this, game, SensorManager.SENSOR_DELAY_GAME);
        if (rot != null) sm.registerListener(this, rot, SensorManager.SENSOR_DELAY_UI);
    }

    @Override
    public void onSensorChanged(SensorEvent e) {
        long now = System.currentTimeMillis();
        boolean isGame = e.sensor.getType() == Sensor.TYPE_GAME_ROTATION_VECTOR;
        if (isGame) { if (now - lastGame < 20) return; lastGame = now; }   // ~50 Hz
        else { if (now - lastRot < 100) return; lastRot = now; }           // ~10 Hz
        SensorManager.getRotationMatrixFromVector(m, e.values);
        JSArray a = new JSArray();
        for (float v : m) a.put(Double.valueOf(v)); // put(Object): no checked JSONException
        JSObject d = new JSObject(); d.put("m", a);
        notifyListeners(isGame ? "game" : "rot", d);
    }

    @Override public void onAccuracyChanged(Sensor sensor, int acc) {}
    @Override protected void handleOnPause() { if (sm != null) sm.unregisterListener(this); }
    @Override protected void handleOnResume() { if (sm != null) register(); }
}
