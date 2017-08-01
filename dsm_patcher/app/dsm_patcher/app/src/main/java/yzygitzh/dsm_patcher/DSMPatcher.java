package yzygitzh.dsm_patcher;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

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
    // packageName -> lpparam
    private static Map<String, LoadPackageParam> lpParamMap = new HashMap<>();
    // packageName -> unhook object
    private static Map<String, XC_MethodHook.Unhook> unhookMap = new HashMap<>();

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
        JSONObject dsmRules = DSMRules.getDSMRules();
        if (dsmRules.has(lpparam.packageName)) {
            try {
                hookPackage(lpparam.packageName, dsmRules.getJSONArray(lpparam.packageName));
            } catch (JSONException e) {
                XposedBridge.log(e);
            }
        }
    }

    public static boolean hookDSMRulePackages() {
        JSONObject dsmRules = DSMRules.getDSMRules();
        Iterator<String> keyItr = dsmRules.keys();
        while (keyItr.hasNext()) {
            String packageName = keyItr.next();
            try {
                hookPackage(packageName, dsmRules.getJSONArray(packageName));
            } catch (JSONException e) {
                XposedBridge.log(e);
                return false;
            }
        }
        return true;
    }

    public static void hookPackage(String packageName, JSONArray dsmRuleList) {
        if (!lpParamMap.containsKey(packageName))
            return;
        final LoadPackageParam lpparam = lpParamMap.get(packageName);

        // TODO: Unhook before hook

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
                XposedBridge.log(packageName + ": " + classMethodName + " hooked");
            } catch (JSONException e){
                XposedBridge.log(e);
            }
        }
    }

}