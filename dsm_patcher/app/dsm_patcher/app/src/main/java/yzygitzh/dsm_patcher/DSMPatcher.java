package yzygitzh.dsm_patcher;

import android.os.FileObserver;
import android.util.Log;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.Charset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import static de.robv.android.xposed.XposedHelpers.findAndHookMethod;
import static de.robv.android.xposed.XposedHelpers.setDoubleField;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.callbacks.XC_LoadPackage.LoadPackageParam;

public class DSMPatcher implements IXposedHookLoadPackage {
    final private String dsmFilePath = "/data/system/ReDroid/dsm.json";
    private JSONArray dsmRuleList = null;

    public void handleLoadPackage(final LoadPackageParam lpparam) throws Throwable {
        if (!initDSMRules(lpparam.packageName)) {
            return;
        }

        int ruleListLen = dsmRuleList.length();
        for (int i = 0; i < ruleListLen; i++) {
            try {
                final JSONObject dsmRule = dsmRuleList.getJSONObject(i);

                final String classMethodName = dsmRule.getString("classMethodName");
                int lastDotPos = classMethodName.lastIndexOf(".");
                String className = classMethodName.substring(0, lastDotPos);
                String methodName = classMethodName.substring(lastDotPos + 1);

                String returnType = dsmRule.getString("returnType");

                final JSONArray stackTrace = dsmRule.getJSONArray("stackTrace");

                JSONArray methodParaList = dsmRule.getJSONArray("paraList");
                List<Object> hookMethodParaList = new ArrayList<>();
                int paraListLen = methodParaList.length();
                for (int j = 0; j < paraListLen; j++) {
                    String paraType = methodParaList.getString(j);
                    switch (paraType) {
                        case "int":
                            hookMethodParaList.add(int.class);
                            break;
                        default:
                            hookMethodParaList.add(paraType);
                    }
                }
                XposedBridge.log(lpparam.packageName + ": " + classMethodName + " before hook");

                hookMethodParaList.add(new XC_MethodHook() {
                    @Override
                    protected void beforeHookedMethod(MethodHookParam param) throws Throwable {
                        XposedBridge.log(lpparam.packageName + ": " + classMethodName + " ent");
                    }
                    @Override
                    protected void afterHookedMethod(MethodHookParam param) throws Throwable {
                        // this will be called after the clock was updated by the original method
                        /*
                        StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
                        for (StackTraceElement ele: stackTrace) {
                            String classMethod = ele.getClassName() + "." + ele.getMethodName();
                            XposedBridge.log(classMethod);
                            if (classMethod.equals("diff.strazzere.anti.MainActivity.isDebugged")) {
                                XposedBridge.log("233");
                                param.setResult(false);
                            }
                        }
                        */
                        XposedBridge.log(lpparam.packageName + ": " + classMethodName + " ext");
                    }
                });

                XC_MethodHook.Unhook unhookEntry = findAndHookMethod(className, lpparam.classLoader, methodName, hookMethodParaList.toArray());
                XposedBridge.log(lpparam.packageName + ": " + classMethodName + " hooked");
            } catch (JSONException e){
                XposedBridge.log("hook method failed");
            }
        }
    }

    private boolean initDSMRules(String packageName) {
        File dsmFile = new File(dsmFilePath);
        try {
            FileInputStream fs = new FileInputStream(dsmFile);
            FileChannel fc = fs.getChannel();
            MappedByteBuffer bb = fc.map(FileChannel.MapMode.READ_ONLY, 0, fc.size());
            String jsonStr = Charset.defaultCharset().decode(bb).toString();
            fc.close();
            fs.close();

            JSONObject dsmRules = new JSONObject(jsonStr);
            if (dsmRules.has(packageName)) {
                dsmRuleList = dsmRules.getJSONArray(packageName);
                XposedBridge.log("initDSMRules suceeded for " + packageName);
                return true;
            } else {
                return false;
            }
        } catch (Exception e) {
            XposedBridge.log("initDSMRules failed");
            return false;
        }
    }
}