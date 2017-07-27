package yzygitzh.dsm_patcher;

import static de.robv.android.xposed.XposedHelpers.findAndHookMethod;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XposedBridge;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.callbacks.XC_LoadPackage.LoadPackageParam;

public class DSMPatcher implements IXposedHookLoadPackage {
    public void handleLoadPackage(final LoadPackageParam lpparam) throws Throwable {
        if (!lpparam.packageName.equals("diff.strazzere.anti"))
            return;

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
    }
}