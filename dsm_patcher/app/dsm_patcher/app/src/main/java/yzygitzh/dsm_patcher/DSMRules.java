package yzygitzh.dsm_patcher;

import android.app.Activity;
import android.content.res.Resources;
import android.os.Environment;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.Charset;

import de.robv.android.xposed.XposedBridge;

/**
 * Created by yzy on 7/28/17.
 */

public class DSMRules {
    private static JSONObject dsmRules = null;

    public static Boolean initDSMRules() {
        File dsmFile = new File("/data/system/ReDroid/dsm.json");

        try {
            FileInputStream fs = new FileInputStream(dsmFile);
            FileChannel fc = fs.getChannel();
            MappedByteBuffer bb = fc.map(FileChannel.MapMode.READ_ONLY, 0, fc.size());
            String jsonStr = Charset.defaultCharset().decode(bb).toString();

            dsmRules = new JSONObject(jsonStr);
            return true;
        } catch (Exception e) {
            XposedBridge.log(e.toString());
        }
        return false;
    }

    public static JSONObject getDSMRules() {
        return dsmRules;
    }
}
