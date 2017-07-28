package yzygitzh.dsm_patcher;

import org.json.JSONObject;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import static de.robv.android.xposed.XposedHelpers.findAndHookMethod;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.callbacks.XC_LoadPackage.LoadPackageParam;

public class DSMPatcher implements IXposedHookLoadPackage {
    private static Map<String, LoadPackageParam> lpParamMap = new HashMap<>();

    /*
     * There are 2 phase of method hooking
     * 1. package loading
     * 2. refresh button
     */
    public DSMPatcher() {
        if (DSMRules.initDSMRules()) {
            XposedBridge.log("DSMPatcher: init succeeded");
        } else {
            XposedBridge.log("DSMPatcher: init failed");
        }
    }

    public void handleLoadPackage(final LoadPackageParam lpparam) throws Throwable {
        lpParamMap.put(lpparam.packageName, lpparam);
        hookPackage(lpparam.packageName);
        /*
        findAndHookMethod("android.os.Debug", lpparam.classLoader, "isDebuggerConnected", new XC_MethodHook() {
            @Override
            protected void beforeHookedMethod(MethodHookParam param) throws Throwable {
                // this will be called before the clock was updated by the original method
                XposedBridge.log("###android.os.Debug.isDebuggerConnected: ent: " + lpparam.packageName);
            }
            @Override
            protected void afterHookedMethod(MethodHookParam param) throws Throwable {
                // this will be called after the clock was updated by the original method
                StackTraceElement[] stackTrace = Thread.currentThread().getStackTrace();
                for (StackTraceElement ele: stackTrace) {
                    String classMethod = ele.getClassName() + "." + ele.getMethodName();
                    XposedBridge.log(classMethod);
                    if (classMethod.equals("diff.strazzere.anti.MainActivity.isDebugged")) {
                        XposedBridge.log("233");
                        param.setResult(false);
                    }
                }
                XposedBridge.log("###android.os.Debug.isDebuggerConnected: ext: " + lpparam.packageName);
            }
        });
        */
    }

    public static void hookPackage(String packageName) {
        LoadPackageParam lpparam = lpParamMap.get(packageName);
        if (lpparam != null) {
            XposedBridge.log(packageName + " hooked");
        }
    }

    public static void hookDSMRulePackages() {
        JSONObject dsmRules = DSMRules.getDSMRules();
        Iterator<String> keyItr = dsmRules.keys();
        while (keyItr.hasNext()) hookPackage(keyItr.next());
    }
}