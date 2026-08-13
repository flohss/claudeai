using System.Collections.Generic;
using UnityEngine;

namespace CharacterCustomization
{
    /// <summary>
    /// Equips/unequips clothing prefabs onto the character's existing skeleton by
    /// rebinding each equipped SkinnedMeshRenderer's bones to the matching transforms
    /// on the base skeleton (matched by bone name). This is the standard technique for
    /// swappable clothing on a shared humanoid rig — the clothing prefab's own bones
    /// are only used to build the name lookup, not driven directly.
    /// </summary>
    public class EquipmentManager : MonoBehaviour
    {
        [SerializeField] private Transform skeletonRoot;
        [SerializeField] private SkinnedMeshRenderer bodyRenderer;

        private readonly Dictionary<EquipmentSlot, GameObject> equippedInstances = new Dictionary<EquipmentSlot, GameObject>();
        private readonly Dictionary<EquipmentSlot, ClothingItem> equippedItems = new Dictionary<EquipmentSlot, ClothingItem>();

        private MaterialPropertyBlock propBlock;

        public BodyPartMask BodyPartsHidden { get; private set; }

        private void Awake()
        {
            propBlock = new MaterialPropertyBlock();
        }

        public void Equip(ClothingItem item, Color? tint = null)
        {
            if (item == null || item.prefab == null)
            {
                return;
            }

            Unequip(item.slot);

            var instance = Instantiate(item.prefab, transform);
            RebindToSkeleton(instance, skeletonRoot);

            if (item.allowsColorTint)
            {
                ApplyTint(instance, item.tintProperty, tint ?? item.defaultTint);
            }

            equippedInstances[item.slot] = instance;
            equippedItems[item.slot] = item;

            RecalculateHiddenBodyParts();
        }

        public void Unequip(EquipmentSlot slot)
        {
            if (equippedInstances.TryGetValue(slot, out var instance) && instance != null)
            {
                Destroy(instance);
            }

            equippedInstances.Remove(slot);
            equippedItems.Remove(slot);

            RecalculateHiddenBodyParts();
        }

        public ClothingItem GetEquipped(EquipmentSlot slot)
        {
            return equippedItems.TryGetValue(slot, out var item) ? item : null;
        }

        private void RebindToSkeleton(GameObject instance, Transform skeleton)
        {
            if (skeleton == null)
            {
                return;
            }

            var boneMap = new Dictionary<string, Transform>();
            foreach (var bone in skeleton.GetComponentsInChildren<Transform>())
            {
                boneMap[bone.name] = bone;
            }

            foreach (var smr in instance.GetComponentsInChildren<SkinnedMeshRenderer>())
            {
                var oldBones = smr.bones;
                var newBones = new Transform[oldBones.Length];

                for (int i = 0; i < oldBones.Length; i++)
                {
                    if (oldBones[i] != null && boneMap.TryGetValue(oldBones[i].name, out var match))
                    {
                        newBones[i] = match;
                    }
                    else
                    {
                        newBones[i] = oldBones[i];
                    }
                }

                smr.bones = newBones;

                if (smr.rootBone != null && boneMap.TryGetValue(smr.rootBone.name, out var rootMatch))
                {
                    smr.rootBone = rootMatch;
                }
            }
        }

        private void ApplyTint(GameObject instance, string property, Color color)
        {
            foreach (var renderer in instance.GetComponentsInChildren<Renderer>())
            {
                renderer.GetPropertyBlock(propBlock);
                propBlock.SetColor(property, color);
                renderer.SetPropertyBlock(propBlock);
            }
        }

        private void RecalculateHiddenBodyParts()
        {
            var mask = BodyPartMask.None;
            foreach (var item in equippedItems.Values)
            {
                mask |= item.hiddenBodyParts;
            }

            BodyPartsHidden = mask;

            // Actually hiding vertices depends on how the base body mesh is authored
            // (per-part submeshes vs. a single skinned mesh). Wire a BodyPartVisibility
            // component here that reads BodyPartsHidden and toggles submeshes or a
            // shader mask to match your mesh's setup.
        }
    }
}
