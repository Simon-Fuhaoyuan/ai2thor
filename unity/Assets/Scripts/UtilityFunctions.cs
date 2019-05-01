using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityStandardAssets.CrossPlatformInput;
using UnityStandardAssets.Utility;
public static class UtilityFunctions {
    private static IEnumerable<int[]> Combinations(int m, int n) {
        // Enumerate all possible m-size combinations of [0, 1, ..., n-1] array
        // in lexicographic order (first [0, 1, 2, ..., m-1]).
        // Taken from https://codereview.stackexchange.com/questions/194967/get-all-combinations-of-selecting-k-elements-from-an-n-sized-array
        int[] result = new int[m];
        Stack<int> stack = new Stack<int>(m);
        stack.Push(0);
        while (stack.Count > 0) {
            int index = stack.Count - 1;
            int value = stack.Pop();
            while (value < n) {
                result[index++] = value++;
                stack.Push(value);
                if (index != m) continue;
                yield return (int[])result.Clone(); // thanks to @xanatos
                //yield return result;
                break;
            }
        }
    }

    public static IEnumerable<T[]> Combinations<T>(T[] array, int m) {
        // Taken from https://codereview.stackexchange.com/questions/194967/get-all-combinations-of-selecting-k-elements-from-an-n-sized-array
        if (array.Length < m) {
            throw new ArgumentException("Array length can't be less than number of selected elements");
        }
        if (m < 1) {
            throw new ArgumentException("Number of selected elements can't be less than 1");
        }
        T[] result = new T[m];
        foreach (int[] j in Combinations(m, array.Length)) {
            for (int i = 0; i < m; i++) {
                result[i] = array[j[i]];
            }
            yield return result;
        }
    }

    public static bool isObjectColliding(GameObject go, List<GameObject> ignoreGameObjects = null, float expandBy = 0.0f) {
        if (ignoreGameObjects == null) {
            ignoreGameObjects = new List<GameObject>();
        }
        ignoreGameObjects.Add(go);
        HashSet<Collider> ignoreColliders = new HashSet<Collider>();
        foreach (GameObject toIgnoreGo in ignoreGameObjects) {
            foreach (Collider c in toIgnoreGo.GetComponentsInChildren<Collider>()) {
                ignoreColliders.Add(c);
            }
        }

        int layerMask = 1 << 8;
        foreach (CapsuleCollider cc in go.GetComponentsInChildren<CapsuleCollider>()) {
            foreach (Collider c in PhysicsExtensions.OverlapCapsule(cc, layerMask, QueryTriggerInteraction.Ignore, expandBy)) {
                if (!ignoreColliders.Contains(c)) {
                    return true;
                }
            }
        }
        foreach (BoxCollider bc in go.GetComponentsInChildren<BoxCollider>()) {
            foreach (Collider c in PhysicsExtensions.OverlapBox(bc, layerMask, QueryTriggerInteraction.Ignore, expandBy)) {
                if (!ignoreColliders.Contains(c)) {
                    return true;
                }
            }
        }
        foreach (SphereCollider sc in go.GetComponentsInChildren<SphereCollider>()) {
            foreach (Collider c in PhysicsExtensions.OverlapSphere(sc, layerMask, QueryTriggerInteraction.Ignore, expandBy)) {
                if (!ignoreColliders.Contains(c)) {
                    return true;
                }
            }
        }
        return false;
    }

    public static Collider[] collidersObjectCollidingWith(GameObject go, List<GameObject> ignoreGameObjects = null, float expandBy = 0.0f) {
        if (ignoreGameObjects == null) {
            ignoreGameObjects = new List<GameObject>();
        }
        ignoreGameObjects.Add(go);
        HashSet<Collider> ignoreColliders = new HashSet<Collider>();
        foreach (GameObject toIgnoreGo in ignoreGameObjects) {
            foreach (Collider c in toIgnoreGo.GetComponentsInChildren<Collider>()) {
                ignoreColliders.Add(c);
            }
        }

        HashSet<Collider> collidersSet = new HashSet<Collider>();
        int layerMask = 1 << 8 | 1 << 10;
        foreach (CapsuleCollider cc in go.GetComponentsInChildren<CapsuleCollider>()) {
            foreach (Collider c in PhysicsExtensions.OverlapCapsule(cc, layerMask, QueryTriggerInteraction.Ignore, expandBy)) {
                if (!ignoreColliders.Contains(c)) {
                    collidersSet.Add(c);
                }
            }
        }
        foreach (BoxCollider bc in go.GetComponentsInChildren<BoxCollider>()) {
            foreach (Collider c in PhysicsExtensions.OverlapBox(bc, layerMask, QueryTriggerInteraction.Ignore, expandBy)) {
                if (!ignoreColliders.Contains(c)) {
                    collidersSet.Add(c);
                }
            }
        }
        foreach (SphereCollider sc in go.GetComponentsInChildren<SphereCollider>()) {
            foreach (Collider c in PhysicsExtensions.OverlapSphere(sc, layerMask, QueryTriggerInteraction.Ignore, expandBy)) {
                if (!ignoreColliders.Contains(c)) {
                    collidersSet.Add(c);
                }
            }
        }
        return collidersSet.ToArray();
    }

    public static RaycastHit[] CastAllPrimitiveColliders(GameObject go, Vector3 direction, float maxDistance = Mathf.Infinity, int layerMask = Physics.DefaultRaycastLayers, QueryTriggerInteraction queryTriggerInteraction = QueryTriggerInteraction.UseGlobal) {
        List<RaycastHit> hits = new List<RaycastHit>();
        foreach (CapsuleCollider cc in go.GetComponentsInChildren<CapsuleCollider>()) {
            foreach (RaycastHit h in PhysicsExtensions.CapsuleCastAll(cc, direction, maxDistance, layerMask, queryTriggerInteraction)) {
                hits.Add(h);
            }
        }
        foreach (BoxCollider bc in go.GetComponentsInChildren<BoxCollider>()) {
            foreach (RaycastHit h in PhysicsExtensions.BoxCastAll(bc, direction, maxDistance, layerMask, queryTriggerInteraction)) {
                hits.Add(h);
            }
        }
        foreach (SphereCollider sc in go.GetComponentsInChildren<SphereCollider>()) {
            foreach (RaycastHit h in PhysicsExtensions.SphereCastAll(sc, direction, maxDistance, layerMask, queryTriggerInteraction)) {
                hits.Add(h);
            }
        }
        return hits.ToArray();
    }

}