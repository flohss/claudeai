using System;
using UnityEngine;

namespace CharacterCustomization
{
    [Flags]
    public enum BodyPartMask
    {
        None = 0,
        Torso = 1 << 0,
        Legs = 1 << 1,
        Feet = 1 << 2,
        Hands = 1 << 3,
        Head = 1 << 4
    }

    [CreateAssetMenu(menuName = "Character Customization/Clothing Item", fileName = "ClothingItem")]
    public class ClothingItem : ScriptableObject
    {
        [Tooltip("Stable identifier used in save data and catalog lookups.")]
        public string id;

        public string displayName;
        public EquipmentSlot slot;

        [Tooltip("Prefab rigged to the same skeleton (matching bone names) as the base body.")]
        public GameObject prefab;

        public bool allowsColorTint = true;
        public Color defaultTint = Color.white;
        public string tintProperty = "_BaseColor";

        [Tooltip("Body parts of the base mesh to hide while this item is equipped, so skin doesn't poke through clothing.")]
        public BodyPartMask hiddenBodyParts;
    }
}
